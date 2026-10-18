import os
import sys
import uuid
from datetime import datetime, timezone

# Ensure project root is in sys.path when running script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models import (
    User, WorkerProfile, Job, JobVerification,
    UserRole, UserStatus, JobStatus, VerificationResult
)
from app.core.security import hash_password
from app.core.phone import normalize_phone

DEMO_JOBS = [
    {
        "title": "Steel Fixer",
        "city": "Riyadh",
        "country": "Saudi Arabia",
        "category": "Structural",
        "salary_min": 1900,
        "salary_max": 2200,
        "salary_currency": "SAR",
        "salary_period": "mo",
        "description": "Experienced steel fixers required for large-scale commercial foundation and structural reinforcement projects in Riyadh. Free accommodation, transport, and medical insurance provided.",
        "requirements": "Minimum 2 years commercial rebar / steel fixing experience. Ability to read reinforcement drawings. Valid passport.",
        "employer_name": "Al-Bawani Contracting Co.",
        "verified": True,
        "evidence": "CR-1010023481 (Ministry of Commerce Registry)"
    },
    {
        "title": "Mason",
        "city": "Dubai",
        "country": "UAE",
        "category": "Structural",
        "salary_min": 1700,
        "salary_max": 2000,
        "salary_currency": "AED",
        "salary_period": "mo",
        "description": "Block, brick, and plaster masons needed for high-rise residential construction in Downtown Dubai. Overtime opportunities available.",
        "requirements": "At least 3 years experience in blockwork, bricklaying, and plastering. Trade test certification preferred.",
        "employer_name": "Arabtec Construction LLC",
        "verified": True,
        "evidence": "DED Licence #529810 (Dubai Economy & Tourism)"
    },
    {
        "title": "Scaffolder",
        "city": "Dammam",
        "country": "Saudi Arabia",
        "category": "Structural",
        "salary_min": 1800,
        "salary_max": 2100,
        "salary_currency": "SAR",
        "salary_period": "mo",
        "description": "CISRS / equivalent certified scaffolders required for industrial refinery site maintenance and erection.",
        "requirements": "Certified scaffolding training certificate. 2+ years erection and dismantling at height. Safety-first mindset.",
        "employer_name": "Nesma & Partners Contracting Co.",
        "verified": True,
        "evidence": "Aramco Contractor Approval Ref #NES-994"
    },
    {
        "title": "Site Electrician",
        "city": "Abu Dhabi",
        "country": "UAE",
        "category": "MEP",
        "salary_min": 2100,
        "salary_max": 2500,
        "salary_currency": "AED",
        "salary_period": "mo",
        "description": "Installation of cable trays, conduit bending, wire pulling, DB terminations and testing for infrastructure substation projects.",
        "requirements": "Diploma or trade certificate in Electrical Engineering. 3+ years Gulf or local commercial electrical experience.",
        "employer_name": "Target Engineering Construction",
        "verified": True,
        "evidence": "Abu Dhabi Chamber of Commerce Reg #7721"
    },
    {
        "title": "Plumber",
        "city": "Doha",
        "country": "Qatar",
        "category": "MEP",
        "salary_min": 2000,
        "salary_max": 2300,
        "salary_currency": "QAR",
        "salary_period": "mo",
        "description": "Sanitary and drainage piping installation, PPR hot/cold water supply, pressure testing for hospital development project.",
        "requirements": "Plumbing trade test certificate. Knowledge of drainage stacks and water distribution systems.",
        "employer_name": "Midmac Contracting Co.",
        "verified": True,
        "evidence": "Qatar Commercial Registration #11452"
    },
    {
        "title": "Pipe Welder",
        "city": "Jubail",
        "country": "Saudi Arabia",
        "category": "MEP",
        "salary_min": 2800,
        "salary_max": 3400,
        "salary_currency": "SAR",
        "salary_period": "mo",
        "description": "6G TIG and Arc welders for carbon steel and stainless steel process piping on industrial petrochemical site.",
        "requirements": "6G certification (ASME Section IX). Minimum 4 years heavy industrial pipe welding experience.",
        "employer_name": "Al-Yusr Industrial Contracting (AYTB)",
        "verified": True,
        "evidence": "Sabic Approved Vendor Ref #AYTB-8802"
    },
    {
        "title": "Painter",
        "city": "Sharjah",
        "country": "UAE",
        "category": "Finishing",
        "salary_min": 1500,
        "salary_max": 1800,
        "salary_currency": "AED",
        "salary_period": "mo",
        "description": "Interior and exterior emulsion painting, putty application, roller and spray finishing for luxury villas.",
        "requirements": "Proven experience in surface preparation, primer application, and high-quality paint finish.",
        "employer_name": "Sharjah National Contracting",
        "verified": True,
        "evidence": "SEDD Trade Licence #34910"
    },
    {
        "title": "Carpenter",
        "city": "Jeddah",
        "country": "Saudi Arabia",
        "category": "Finishing",
        "salary_min": 2000,
        "salary_max": 2400,
        "salary_currency": "SAR",
        "salary_period": "mo",
        "description": "Shuttering carpenters and finishing joiners for waterfront hospitality development. Formwork and door/window installations.",
        "requirements": "3+ years timber and ply shuttering or architectural joinery experience.",
        "employer_name": "Saudi Binladin Group (SBG)",
        "verified": True,
        "evidence": "MCI Commercial License #403001"
    },
    {
        "title": "Excavator Operator",
        "city": "Doha",
        "country": "Qatar",
        "category": "Equipment & Site",
        "salary_min": 2600,
        "salary_max": 3000,
        "salary_currency": "QAR",
        "salary_period": "mo",
        "description": "Heavy hydraulic excavator operators for trenching, deep basement excavation, and site grading.",
        "requirements": "Valid heavy equipment operator driving licence (Qatar or GCC licence preferred, or valid national licence). 3+ years operating 20T+ excavators.",
        "employer_name": "HBK Contracting Co.",
        "verified": True,
        "evidence": "Ashghal Prequalified Contractor #HBK-108"
    },
    {
        "title": "Site Foreman",
        "city": "Dubai",
        "country": "UAE",
        "category": "Equipment & Site",
        "salary_min": 3800,
        "salary_max": 4500,
        "salary_currency": "AED",
        "salary_period": "mo",
        "description": "Supervising multi-disciplinary trade crews, enforcing HSE site compliance, tracking daily progress logs and materials.",
        "requirements": "Diploma in Civil Engineering or equivalent 5+ years site supervisory experience. Good English communication skills.",
        "employer_name": "Sobha Constructions LLC",
        "verified": True,
        "evidence": "Dubai Municipality Approved Supervisor Ref #DM-SOBHA-421"
    }
]

def seed_data():
    from app.core.config import settings
    if settings.IS_PRODUCTION:
        sys.exit("Refusing to seed demo data (known passwords, fake jobs) when APP_ENV=production. "
                 "Use scripts/create_admin.py instead.")
    db: Session = SessionLocal()
    try:
        # 1. Seed or retrieve default administrator
        admin_phone = normalize_phone("+254700000001")
        admin = db.query(User).filter(User.phone == admin_phone).first()
        if not admin:
            admin = User(
                phone=admin_phone,
                email="admin@toplinejobs.com",
                password_hash=hash_password("TopLineAdmin2026!"),
                role=UserRole.ADMINISTRATOR,
                status=UserStatus.ACTIVE,
                phone_verified_at=datetime.now(timezone.utc)
            )
            db.add(admin)
            db.flush()
            admin_profile = WorkerProfile(
                user_id=admin.id,
                full_name="TopLine System Administrator",
                trade="Administration",
                preferred_country="Kenya"
            )
            db.add(admin_profile)
            db.commit()
            print(f"Created default administrator: {admin.phone} (email: {admin.email})")

        # 2. Seed Demo Workers (Already Activated with Entitlements & Applications)
        demo_workers = [
            {
                "phone": "+254711000001",
                "email": "kamau.mason@topline.com",
                "name": "John Kamau",
                "trade": "Mason",
                "country": "Saudi Arabia",
                "pass": "WorkerPass2026!"
            },
            {
                "phone": "+254711000002",
                "email": "ochieng.electrician@topline.com",
                "name": "Peter Ochieng",
                "trade": "Electrician",
                "country": "UAE",
                "pass": "WorkerPass2026!"
            },
            {
                "phone": "+254711000003",
                "email": "mwangi.welder@topline.com",
                "name": "Samuel Mwangi",
                "trade": "Welder",
                "country": "Qatar",
                "pass": "WorkerPass2026!"
            }
        ]

        from app.models import Entitlement, EntitlementType, Payment, PaymentStatus, JobApplication, ApplicationStatus

        seeded_worker_users = []
        for w_data in demo_workers:
            norm_phone = normalize_phone(w_data["phone"])
            worker = db.query(User).filter(User.phone == norm_phone).first()
            if not worker:
                worker = User(
                    phone=norm_phone,
                    email=w_data["email"],
                    password_hash=hash_password(w_data["pass"]),
                    role=UserRole.WORKER,
                    status=UserStatus.ACTIVE,
                    phone_verified_at=datetime.now(timezone.utc)
                )
                db.add(worker)
                db.flush()

                profile = WorkerProfile(
                    user_id=worker.id,
                    full_name=w_data["name"],
                    trade=w_data["trade"],
                    preferred_country=w_data["country"]
                )
                db.add(profile)

                # Seed Confirmed Payment & Active Platform Entitlement
                payment = Payment(
                    user_id=worker.id,
                    purpose="platform_access",
                    amount_minor=100000,
                    currency="KES",
                    provider="mpesa",
                    provider_reference=f"MPE_{uuid.uuid4().hex[:8].upper()}",
                    status=PaymentStatus.CONFIRMED,
                    confirmed_at=datetime.now(timezone.utc)
                )
                db.add(payment)
                db.flush()

                entitlement = Entitlement(
                    user_id=worker.id,
                    entitlement_type=EntitlementType.PLATFORM_ACCESS,
                    source_payment_id=payment.id,
                    granted_at=datetime.now(timezone.utc),
                    expires_at=None
                )
                db.add(entitlement)
                print(f"Seeded activated demo worker: {w_data['name']} ({norm_phone})")

            seeded_worker_users.append(worker)

        # 3. Seed Jobs
        seeded_jobs = []
        for item in DEMO_JOBS:
            job = db.query(Job).filter(Job.title == item["title"], Job.city == item["city"]).first()
            if not job:
                job = Job(
                    created_by=admin.id,
                    title=item["title"],
                    category=item["category"],
                    country=item["country"],
                    city=item["city"],
                    salary_min=item["salary_min"],
                    salary_max=item["salary_max"],
                    salary_currency=item["salary_currency"],
                    salary_period=item["salary_period"],
                    description=item["description"],
                    requirements=item["requirements"],
                    employer_name=item["employer_name"],
                    status=JobStatus.PUBLISHED,
                    published_at=datetime.now(timezone.utc)
                )
                db.add(job)
                db.flush()

                if item.get("verified"):
                    verification = JobVerification(
                        job_id=job.id,
                        reviewer_id=admin.id,
                        verification_type="employer_licence_and_trade_registry",
                        result=VerificationResult.VERIFIED,
                        evidence_reference=f"[DEMO VERIFICATION] {item['evidence']}",
                        review_notes="Verified via commercial registry check and contractor licence verification (Demo Data).",
                        reviewed_at=datetime.now(timezone.utc)
                    )
                    db.add(verification)

                print(f"Seeded job: {job.title} ({job.city}, {job.country})")

            seeded_jobs.append(job)

        # 4. Seed Sample Application for first demo worker
        if seeded_worker_users and seeded_jobs:
            w1 = seeded_worker_users[0]
            j1 = seeded_jobs[0]
            existing_app = db.query(JobApplication).filter(JobApplication.worker_id == w1.id, JobApplication.job_id == j1.id).first()
            if not existing_app:
                app_rec = JobApplication(
                    worker_id=w1.id,
                    job_id=j1.id,
                    cover_letter="Experienced mason and structural worker ready for deployment to Riyadh. All trade test certifications in order.",
                    status=ApplicationStatus.UNDER_REVIEW
                )
                db.add(app_rec)
                print(f"Seeded sample application for {w1.phone} -> {j1.title}")

        db.commit()
        print("Demo seed completed successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()

