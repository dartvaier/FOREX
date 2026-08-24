"""Optional local Ollama implementation of the bounded LLMProvider interface."""
import json,os
from dataclasses import dataclass
from enum import StrEnum
from multiprocessing import get_context
from queue import Empty
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
from research.agent import LLMProvider
from research.proposal import HypothesisProposal
from research.service import RegisteredStrategy,StrategySpec
class OllamaErrorCode(StrEnum): CONNECTION_REFUSED="CONNECTION_REFUSED"; TIMEOUT="TIMEOUT"; MODEL_NOT_FOUND="MODEL_NOT_FOUND"; PROVIDER_ERROR="PROVIDER_ERROR"; INVALID_OUTPUT="INVALID_OUTPUT"
class OllamaProviderError(RuntimeError):
 def __init__(self,code,message):self.code=code;super().__init__(message)
@dataclass(frozen=True,slots=True)
class OllamaTelemetry: host:str; model:str
def _request_worker(host,payload,timeout,result_queue):
 try:
  req=Request(host+"/api/chat",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"});result_queue.put(("SUCCESS",json.loads(urlopen(req,timeout=timeout).read())))
 except HTTPError as e:result_queue.put(("MODEL_NOT_FOUND" if e.code==404 else "PROVIDER_ERROR","ollama request failed"))
 except URLError:result_queue.put(("CONNECTION_REFUSED","ollama unavailable"))
 except TimeoutError:result_queue.put(("TIMEOUT","ollama timeout"))
 except Exception:result_queue.put(("PROVIDER_ERROR","ollama request failed"))
class OllamaProvider(LLMProvider):
 def __init__(self,host=None,model=None,transport=None,timeout=30): self.host=(host or os.getenv("OLLAMA_HOST","http://localhost:11434")).rstrip("/");self.model=model or os.getenv("OLLAMA_MODEL","qwen3:8b");self.transport=transport or self._http;self.timeout=timeout;self.telemetry=OllamaTelemetry(self.host,self.model)
 def _http(self,payload):
  context=get_context("spawn");result_queue=context.Queue();process=context.Process(target=_request_worker,args=(self.host,payload,self.timeout,result_queue));process.start();process.join(self.timeout)
  if process.is_alive(): process.terminate();process.join();result_queue.close();raise OllamaProviderError(OllamaErrorCode.TIMEOUT,"ollama deadline exceeded")
  try: status,value=result_queue.get(timeout=1)
  except Empty: raise OllamaProviderError(OllamaErrorCode.INVALID_OUTPUT,"ollama returned no result")
  finally: result_queue.close()
  if status!="SUCCESS": raise OllamaProviderError(OllamaErrorCode(status),value)
  return value
 def _ask(self,prompt,schema):
  try: raw=self.transport({"model":self.model,"messages":[{"role":"user","content":prompt}],"stream":False,"think":False,"format":schema,"options":{"temperature":0}});return json.loads(raw["message"]["content"])
  except OllamaProviderError: raise
  except Exception as e: raise OllamaProviderError(OllamaErrorCode.INVALID_OUTPUT,"invalid structured output") from e
 def propose(self,context):
  schema={"type":"object","required":["title","thesis","expected_mechanism","falsification_criteria","assumptions","tags","parameters"],"properties":{"title":{"type":"string"},"thesis":{"type":"string"},"expected_mechanism":{"type":"string"},"falsification_criteria":{"type":"array","items":{"type":"string"}},"assumptions":{"type":"array","items":{"type":"string"}},"tags":{"type":"array","items":{"type":"string"}},"parameters":{"type":"object","required":["fast_period","slow_period"],"properties":{"fast_period":{"type":"integer"},"slow_period":{"type":"integer"}}}}}
  x=self._ask(json.dumps(context,default=str),schema)
  try:return HypothesisProposal(x["title"],x["thesis"],x["expected_mechanism"],StrategySpec(RegisteredStrategy.EMA_CROSSOVER,"EURUSD","H1",x["parameters"]),tuple(x["falsification_criteria"]),tuple(x["assumptions"]),tuple(x["tags"]))
  except Exception as e:raise OllamaProviderError(OllamaErrorCode.INVALID_OUTPUT,"proposal conversion failed") from e
 def assess(self,facts):return self._ask(json.dumps(facts,default=str),{"type":"object","required":["interpretation"],"properties":{"interpretation":{"type":"string"}}})["interpretation"]
