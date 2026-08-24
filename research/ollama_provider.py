"""Optional local Ollama implementation of the bounded LLMProvider interface."""
import json,os
from dataclasses import dataclass
from enum import StrEnum
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
class OllamaProvider(LLMProvider):
 def __init__(self,host=None,model=None,transport=None,timeout=30): self.host=(host or os.getenv("OLLAMA_HOST","http://localhost:11434")).rstrip("/");self.model=model or os.getenv("OLLAMA_MODEL","qwen3:8b");self.transport=transport or self._http;self.timeout=timeout;self.telemetry=OllamaTelemetry(self.host,self.model)
 def _http(self,payload):
  try:
   req=Request(self.host+"/api/chat",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"});return json.loads(urlopen(req,timeout=self.timeout).read())
  except HTTPError as e: raise OllamaProviderError(OllamaErrorCode.MODEL_NOT_FOUND if e.code==404 else OllamaErrorCode.PROVIDER_ERROR,"ollama request failed")
  except URLError as e: raise OllamaProviderError(OllamaErrorCode.CONNECTION_REFUSED,"ollama unavailable") from e
  except TimeoutError as e: raise OllamaProviderError(OllamaErrorCode.TIMEOUT,"ollama timeout") from e
 def _ask(self,prompt,schema):
  try: raw=self.transport({"model":self.model,"messages":[{"role":"user","content":prompt}],"stream":False,"format":schema,"options":{"temperature":0}});return json.loads(raw["message"]["content"])
  except OllamaProviderError: raise
  except Exception as e: raise OllamaProviderError(OllamaErrorCode.INVALID_OUTPUT,"invalid structured output") from e
 def propose(self,context):
  schema={"type":"object","required":["title","thesis","expected_mechanism","falsification_criteria","assumptions","tags","parameters"],"properties":{"title":{"type":"string"},"thesis":{"type":"string"},"expected_mechanism":{"type":"string"},"falsification_criteria":{"type":"array","items":{"type":"string"}},"assumptions":{"type":"array","items":{"type":"string"}},"tags":{"type":"array","items":{"type":"string"}},"parameters":{"type":"object","required":["fast_period","slow_period"],"properties":{"fast_period":{"type":"integer"},"slow_period":{"type":"integer"}}}}}
  x=self._ask(json.dumps(context,default=str),schema)
  try:return HypothesisProposal(x["title"],x["thesis"],x["expected_mechanism"],StrategySpec(RegisteredStrategy.EMA_CROSSOVER,"EURUSD","H1",x["parameters"]),tuple(x["falsification_criteria"]),tuple(x["assumptions"]),tuple(x["tags"]))
  except Exception as e:raise OllamaProviderError(OllamaErrorCode.INVALID_OUTPUT,"proposal conversion failed") from e
 def assess(self,facts):return self._ask(json.dumps(facts,default=str),{"type":"object","required":["interpretation"],"properties":{"interpretation":{"type":"string"}}})["interpretation"]
