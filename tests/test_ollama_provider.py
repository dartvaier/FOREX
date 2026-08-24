import json
from research.ollama_provider import *
seen={}
def transport(payload):
 seen.update(payload)
 return {"message":{"content":json.dumps({"interpretation":"facts unchanged"})}}
def test_local_provider_defaults_and_assessment_with_mock_transport():
 p=OllamaProvider(transport=transport);assert p.model=="qwen3:8b" and p.assess({"gate_status":"PASS"})=="facts unchanged" and seen["think"] is False and seen["options"]=={"temperature":0}
def test_invalid_output_fails_closed():
 try:OllamaProvider(transport=lambda x:{}).assess({}) ;assert False
 except OllamaProviderError as e:assert e.code is OllamaErrorCode.INVALID_OUTPUT
