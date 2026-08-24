import pytest
from research.openai_provider import *
def test_no_credentials_fails_closed(monkeypatch):
 monkeypatch.delenv("OPENAI_API_KEY",raising=False)
 with pytest.raises(ProviderError) as error: OpenAIProvider()
 assert error.value.code is ProviderErrorCode.AUTH_ERROR
class BadClient:
 class responses:
  @staticmethod
  def create(**kw): return type("R",(),{"output_text":"not json"})()
def test_invalid_structured_output_is_not_accepted():
 with pytest.raises(ProviderError) as error: OpenAIProvider(client=BadClient()).assess({"x":1})
 assert error.value.code is ProviderErrorCode.INVALID_OUTPUT
