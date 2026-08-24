"""Thin OpenAI Responses provider with environment-only credentials."""
import json
import os
from dataclasses import dataclass
from enum import StrEnum
from research.agent import LLMProvider
from research.proposal import HypothesisProposal
from research.service import RegisteredStrategy, StrategySpec

class ProviderErrorCode(StrEnum): AUTH_ERROR="AUTH_ERROR"; RATE_LIMITED="RATE_LIMITED"; TIMEOUT="TIMEOUT"; PROVIDER_ERROR="PROVIDER_ERROR"; INVALID_OUTPUT="INVALID_OUTPUT"
class ProviderError(RuntimeError):
 def __init__(self,code:ProviderErrorCode,message:str): self.code=code;super().__init__(message)
@dataclass(frozen=True,slots=True)
class ProviderTelemetry: provider:str; model:str; usage:dict[str,int]|None=None
class OpenAIProvider(LLMProvider):
 def __init__(self,model:str="gpt-5",client=None):
  key=os.environ.get("OPENAI_API_KEY")
  if not key and client is None: raise ProviderError(ProviderErrorCode.AUTH_ERROR,"OPENAI_API_KEY is not configured")
  if client is None:
   try:
    from openai import OpenAI; client=OpenAI(api_key=key)
   except Exception as exc: raise ProviderError(ProviderErrorCode.PROVIDER_ERROR,"OpenAI SDK unavailable") from exc
  self.model,self._client,self.telemetry=model,client,ProviderTelemetry("openai",model)
 def _request(self,prompt,schema):
  try: response=self._client.responses.create(model=self.model,input=prompt,text={"format":{"type":"json_schema","name":"research_output","strict":True,"schema":schema}})
  except Exception as exc:
   text=str(exc).lower(); code=ProviderErrorCode.RATE_LIMITED if "rate" in text else ProviderErrorCode.TIMEOUT if "timeout" in text else ProviderErrorCode.AUTH_ERROR if "auth" in text or "key" in text else ProviderErrorCode.PROVIDER_ERROR; raise ProviderError(code,"provider request failed") from exc
  try: return json.loads(response.output_text)
  except Exception as exc: raise ProviderError(ProviderErrorCode.INVALID_OUTPUT,"structured output was invalid") from exc
 def propose(self,context):
  schema={"type":"object","additionalProperties":False,"required":["title","thesis","expected_mechanism","falsification_criteria","parameter_rationale","assumptions","tags","parameters"],"properties":{"title":{"type":"string"},"thesis":{"type":"string"},"expected_mechanism":{"type":"string"},"falsification_criteria":{"type":"array","items":{"type":"string"}},"parameter_rationale":{"type":"array","items":{"type":"string"}},"assumptions":{"type":"array","items":{"type":"string"}},"tags":{"type":"array","items":{"type":"string"}},"parameters":{"type":"object","additionalProperties":False,"required":["fast_period","slow_period"],"properties":{"fast_period":{"type":"integer"},"slow_period":{"type":"integer"}}}}}
  raw=self._request(json.dumps(context,default=str),schema)
  try: return HypothesisProposal(raw["title"],raw["thesis"],raw["expected_mechanism"],StrategySpec(RegisteredStrategy.EMA_CROSSOVER,"EURUSD","H1",raw["parameters"]),tuple(raw["falsification_criteria"]),tuple(raw["parameter_rationale"]),tuple(raw["assumptions"]),tuple(raw["tags"]))
  except Exception as exc: raise ProviderError(ProviderErrorCode.INVALID_OUTPUT,"proposal schema conversion failed") from exc
 def assess(self,facts): return self._request(json.dumps(facts,default=str),{"type":"object","additionalProperties":False,"required":["interpretation"],"properties":{"interpretation":{"type":"string"}}})["interpretation"]
