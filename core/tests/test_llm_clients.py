from typing import LiteralString

from core.utils.llm_clients import GoogleClient


def test_net_access():
    url = "https://www.linkedin.com/jobs/view/4222740714/?eBP=CwEAAAGWnj3Q6RHuWVL4WpCfWYCcFpHt3_HzJP4I96vb1hl6n2vJcPMplxqtJriQvqFb2tFgnB6RVAHEF2cJltdBtPMZhPmixBR4Brpqo1kjvenS2Fn-n9T11DkegOiwsVwJJSFELyRbAyTSuC4oya2ssq3YkqeLmr-MSD3_JtyGb-3Eaa-jqQ6X4KMf1I7DBiM07Ecd08MLRO3T1nT0kbn7X6Ci7xlCRnUAj4DXQPnZtLWEq1al09-6TRzFrr6QbClQlVt7QyKM3bekeLEPGmnKNeWfNWj5kLZYqsudaFyZa-PLiy3zYnqtAlJz3lzuJxOvp64IFgXtvBO9qdGE3fY0nUU5NR_ysxWANLKH1gsOQMj6ZQ7APx1pjKYt8dGWLHzsWS70WA-Y5KwMYBEPYd-OFjWCRTeuLbVEvVA2szycYvNYq_w7dEENB70ZaOzJXqbcR7S026B6HJgde9lohktbbR7vrQs&refId=2LWLYtiXR7OSCripgD2Fog%3D%3D&trackingId=Qo%2Fnh%2FwguQ4gI%2FfVxA9e1Q%3D%3D&trk=flagship3_search_srp_jobs"
    prompt: LiteralString = (
        f"""I am curious to see if you can read whatever it is on this url: {url}"""
    )

    llm = GoogleClient(model="gemini-1.5-pro").generate_text(prompt=prompt, temperature=0.0)
    return llm


resp = test_net_access()
print(resp)
