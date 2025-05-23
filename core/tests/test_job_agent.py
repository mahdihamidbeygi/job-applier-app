import logging
import os
import sys

import django

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
# --- End Django Setup ---

import logging
from typing import Any, Dict

# Now import Django models and other components
from django.contrib.auth import get_user_model

from core.models import UserProfile  # Needed if creating profile
from core.utils.agents.job_agent import JobAgent
from core.utils.agents.personal_agent import PersonalAgent

# Configure logging (optional but helpful)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


test_text = """
About the job
Who we are

Geotab ® is a global leader in IoT and connected transportation and certified “Great Place to Work™.” 
We are a company of diverse and talented individuals who work together to help businesses grow and succeed, and increase the safety and sustainability of our communities.

Geotab is advancing security, connecting commercial vehicles to the internet and providing web-based analytics to help customers better manage their fleets. 
Geotab’s open platform and Geotab Marketplace ®, offering hundreds of third-party solution options, allows both small and large businesses to automate operations by integrating vehicle data with their other data assets. 
Processing billions of data points a day, Geotab leverages data analytics and machine learning to improve productivity, optimize fleets through the reduction of fuel consumption, enhance driver safety and achieve strong compliance to regulatory changes.

Our team is growing and we’re looking for people who follow their passion, think differently and want to make an impact. Ours is a fast paced, ever changing environment. 
Geotabbers accept that challenge and are willing to take on new tasks and activities - ones that may not always be described in the initial job description. 
Join us for a fulfilling career with opportunities to innovate, great benefits, and our fun and inclusive work culture. Reach your full potential with Geotab. 
To see what it’s like to be a Geotabber, check out our blog and follow us @InsideGeotab on Instagram. Join our talent network to learn more about job opportunities and company news.

Who You Are

We are always looking for amazing talent who can contribute to our growth and deliver results! 
Geotab is seeking a Data Scientist to explores and examines data from multiple sources in order to design and construct new data modeling processes using prototypes, algorithms, predictive models, and custom analyses. 
If you love technology, and are keen to join an industry leader — we would love to hear from you!

What You'll Do

The Data Scientist assists in the design and construction of Geotab's data mining and model building processes from vast amounts of raw data. 
This position collaborates with internal technical teams in analyzing trends to make improved decision-making in producing effective customer-facing products.

How You'll Make An Impact

Design and construct Geotab’s data modeling processes.
Create algorithms and predictive models to extract information required to solve complex business problems.
Generate queries from Geotab’s Big Data Infrastructure from Data Warehousing database (i.e. Google BigQuery).
Use Machine Learning (ML) packages (e.g. Scikit-learn and Tensorflow) to develop ML models and features.
Test the performance of data-driven products and make recommendations for improving Geotab’s product suite.
Collaborate with internal technical teams to gather requirements.
Responsible for the design, development, and maintenance of ongoing metrics, reports, analyses, and dashboards to drive key business decisions.
Support a platform providing ad-hoc and automated access to large datasets.

What You'll Bring To The Role

2-5 years experience as a Data Scientist or a similar role.
Understanding of machine learning and operations research.
Thorough knowledge of programming languages (e.g. Python, SQL, C++) and object-oriented programming.
Thorough knowledge of Big Data tools and Data Mining/Warehousing Programs (e.g. Google BigQuery). 
Experience with machine learning techniques (e.g. Scikit-learn, Tensorflow).
Experience using/building business intelligence tools (e.g. Tableau) and data frameworks.
Experience working within a technical or engineering organization, with knowledge of the high-technology industry is an asset.
High accuracy and meticulous attention to detail.
Highly organized and able to manage multiple tasks and projects simultaneously.
Must stay relevant to technology and should have the flexibility to adapt to the growing technology and market demands.
Strong analytical skills with the ability to problem solve well-judged decisions.
Strong team-player with the ability to engage with all levels of the organization.
Technical competence using software programs, including but not limited to, Google Suite for business (Sheets, Docs, Slides).
Entrepreneurial mindset and comfortable in a flat organization.

If you got this far, we hope you're feeling excited about this role! Even if you don't feel you meet every single requirement, we still encourage you to apply.

Please note: Geotab does not accept agency resumes and is not responsible for any fees related to unsolicited resumes. Please do not forward resumes to Geotab employees.

Why job seekers choose Geotab

Flex working arrangements

Home office reimbursement program

Baby bonus & parental leave top up program

Online learning and networking opportunities

Electric vehicle purchase incentive program

Competitive medical and dental benefits

Retirement savings program

The above are offered to full-time permanent employees only

How we work

At Geotab, we have adopted a flexible hybrid working model in that we have systems, functions, programs and policies in place to support both in-person and virtual work.
However, you are welcomed and encouraged to come into our beautiful, safe, clean offices as often as you like. When working from home, you are required to have a reliable internet connection with at least 50mb DL/10mb UL. 
Virtual work is supported with cloud-based applications, collaboration tools and asynchronous working. The health and safety of employees are a top priority. 
We encourage work-life balance and keep the Geotab culture going strong with online social events, chat rooms and gatherings. Join us and help reshape the future of technology!

Geotab verifies candidates' eligibility to work in the United States through E-Verify, an internet-based system operated by U.S. Citizen and Immigration Services.

Other Employment Statements

Geotab will not discharge or in any other manner discriminate against employees or applicants because they have inquired about, discussed, or disclosed their own pay or the pay of another employee or applicant. 
Additionally, employees who have access to the compensation information of other employees or applicants as a part of their essential job functions cannot disclose 
the pay of other employees or applicants to individuals who do not otherwise have access to compensation information, unless the disclosure is (a) in response to a formal complaint or charge, 
(b) in furtherance of an investigation, proceeding, hearing, or action, including an investigation conducted by the employer, or (c) consistent with the Company's legal duty to furnish information.

We are committed to accommodating people with disabilities during the recruitment and assessment processes and when people are hired. 
We will ensure the accessibility needs of employees with disabilities are taken into account as part of performance management, career development, training and redeployment processes. 
If you require accommodation at any stage of the application process or want more information about our diversity and inclusion as well as accommodation policies and practices, 
please contact us at careers@geotab.com. Geotab provides equal employment opportunities (EEO) to all employees and applicants for employment without regard to race, color, religion, sex, national origin, age, disability or genetics. 
In addition to federal law requirements, Geotab complies with applicable state and local laws governing nondiscrimination in employment in every location in which the company has facilities. 
This policy applies to all terms and conditions of employment, including recruiting, hiring, placement, promotion, termination, layoff, recall, transfer, leaves of absence, compensation and training. 
Geotab expressly prohibits any form of workplace harassment or discrimination based on race, color, religion, gender, sexual orientation, gender identity or expression, national origin, age, genetic information, disability, or veteran status. 
Improper interference with the ability of Geotab's employees to perform their job duties may result in discipline up to and including discharge. If you would like more information about our EEO program or wish to file a complaint, 
please contact our EEO officer, Klaus Boeckers at HRCompliance@geotab.com. For more details, view a copy of the EEOC's Know Your Rights poster. By submitting a job application to Geotab Inc. or its affiliates and subsidiaries (collectively, “Geotab”), 
you acknowledge Geotab’s collection, use and disclosure of your personal data in accordance with our Privacy Policy. Click here to learn more about what happens with your personal data. user: testuser
"""


def run_test():
    logger.info("Starting JobAgent test...")

    # --- Get or Create a Test User ---
    User = get_user_model()
    test_username = "test_job_agent_user"
    user, created = User.objects.get_or_create(
        username=test_username,
        defaults={"email": f"{test_username}@example.com", "password": "testpassword"},
    )
    if created:
        logger.info(f"Created test user: {test_username} (ID: {user.id})")
        # Ensure profile exists (post_save signal should handle this, but check just in case)
        UserProfile.objects.get_or_create(user=user)
    else:
        logger.info(f"Using existing test user: {test_username} (ID: {user.id})")
    # --- End User Setup ---

    try:
        logger.info(f"Instantiating JobAgent for user ID: {user.id} with test text...")
        # --- Pass user_id to JobAgent ---
        job_agent = JobAgent(user_id=user.id, text=test_text)
        # --- End Pass user_id ---

        # --- Check if job was created ---
        if job_agent.job_record and job_agent.job_record.id:
            logger.info(
                f"JobAgent successfully created JobListing with ID: {job_agent.job_record.id}"
            )
            logger.info(f"Title: {job_agent.job_record.title}")
            logger.info(f"Company: {job_agent.job_record.company}")
            # logger.info(f"Description Snippet: {job_agent.job_record.description[:200]}...") # Optional: print snippet
        else:
            logger.error("JobAgent did NOT create a JobListing record.")
        # --- End Check ---

    except ValueError as ve:
        logger.error(f"ValueError during JobAgent processing: {ve}")
    except Exception as e:
        logger.exception(
            f"An unexpected error occurred during the test: {e}"
        )  # Use logger.exception


def test_calculate_match_score():
    # Initialize PersonalAgent to get user profile data
    personal_agent = PersonalAgent(user_id=1)
    user_background: Dict[str, Any] = personal_agent.get_formatted_background()

    job_agent = JobAgent(user_id=1, job_id=346)

    score, details = job_agent.calculate_match_score(user_background)
    return (score, details)


if __name__ == "__main__":
    run_test()
    test_calculate_match_score()
