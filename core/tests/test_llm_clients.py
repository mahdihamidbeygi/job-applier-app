import os
import sys

import django

from pathlib import Path

# --- Add Django Setup ---
# Add the project root directory to Python path if running script directly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "job_applier.settings")
try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)

from core.utils.llm_clients import GoogleClient
from pathlib import Path


# def test_net_access():
#     url = "https://www.linkedin.com/jobs/view/4222740714/?eBP=CwEAAAGWnj3Q6RHuWVL4WpCfWYCcFpHt3_HzJP4I96vb1hl6n2vJcPMplxqtJriQvqFb2tFgnB6RVAHEF2cJltdBtPMZhPmixBR4Brpqo1kjvenS2Fn-n9T11DkegOiwsVwJJSFELyRbAyTSuC4oya2ssq3YkqeLmr-MSD3_JtyGb-3Eaa-jqQ6X4KMf1I7DBiM07Ecd08MLRO3T1nT0kbn7X6Ci7xlCRnUAj4DXQPnZtLWEq1al09-6TRzFrr6QbClQlVt7QyKM3bekeLEPGmnKNeWfNWj5kLZYqsudaFyZa-PLiy3zYnqtAlJz3lzuJxOvp64IFgXtvBO9qdGE3fY0nUU5NR_ysxWANLKH1gsOQMj6ZQ7APx1pjKYt8dGWLHzsWS70WA-Y5KwMYBEPYd-OFjWCRTeuLbVEvVA2szycYvNYq_w7dEENB70ZaOzJXqbcR7S026B6HJgde9lohktbbR7vrQs&refId=2LWLYtiXR7OSCripgD2Fog%3D%3D&trackingId=Qo%2Fnh%2FwguQ4gI%2FfVxA9e1Q%3D%3D&trk=flagship3_search_srp_jobs"
#     prompt: LiteralString = (
#         f"""I am curious to see if you can read whatever it is on this url: {url}"""
#     )

#     llm = GoogleClient(model="gemini-1.5-pro").generate_text(prompt=prompt, temperature=0.0)
#     return llm


def test_uploading_file_google():
    resume_path = Path(
        r"C:\Users\mhami\projects\job-applier-app\media\resumes\mhami\Mahdi_Hamidbeygi_resume_pubs.pdf"
    )
    llm = GoogleClient()
    file_input = llm.upload_file(file_path=resume_path)

    resp = llm.client.models.generate_content(
        model="gemini-2.5-flash-preview-04-17",
        contents=[file_input, "What is the name of the person in the resume? "],
    )
    return resp
