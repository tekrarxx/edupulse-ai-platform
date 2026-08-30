"""One-time setup for tests/load/locustfile.py: a real SUPER_ADMIN account,
one skill, and a pool of auto-gradable APPLICATION questions on it. Printed
values feed the locustfile's LOAD_TEST_SKILL_ID / LOAD_TEST_QUESTION_IDS
environment variables — the load test itself never creates curriculum data
inline, so its measured throughput reflects the attempt/decision/dashboard
endpoints under test, not question-creation overhead.

Usage (from inside the api container):
    python3 scripts/seed_load_test_curriculum.py [--question-count N]
"""
import argparse
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.curriculum import Concept, Skill, SkillFacetType, Subject, Topic
from app.models.assessment import Question
from app.models.tenant import Tenant, TenantType
from app.models.user import Role, User


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question-count", type=int, default=20)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        tenant = Tenant(name="Load Test Tenant", tenant_type=TenantType.SCHOOL)
        db.add(tenant)
        db.flush()

        admin = User(
            tenant_id=tenant.id,
            email=f"loadtest-admin-{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password(uuid.uuid4().hex),
            display_name="Load Test Admin",
            role=Role.SUPER_ADMIN,
        )
        db.add(admin)
        db.flush()

        suffix = uuid.uuid4().hex[:8]
        subject = Subject(slug=f"loadtest-subject-{suffix}", name="Load Test Subject")
        db.add(subject)
        db.flush()
        topic = Topic(subject_id=subject.id, slug=f"loadtest-topic-{suffix}", name="Load Test Topic")
        db.add(topic)
        db.flush()
        concept = Concept(topic_id=topic.id, slug=f"loadtest-concept-{suffix}", name="Load Test Concept")
        db.add(concept)
        db.flush()
        skill = Skill(concept_id=concept.id, slug=f"loadtest-skill-{suffix}", name="Load Test Skill")
        db.add(skill)
        db.flush()

        question_ids = []
        for i in range(args.question_count):
            question = Question(
                skill_id=skill.id,
                facet_type=SkillFacetType.APPLICATION,
                prompt=f"Load test question {i}: 2+2=?",
                correct_answer="4",
            )
            db.add(question)
            db.flush()
            question_ids.append(question.id)

        db.commit()

        print(f"LOAD_TEST_SKILL_ID={skill.id}")
        print(f"LOAD_TEST_QUESTION_IDS={','.join(question_ids)}")
        print(f"# tenant_id={tenant.id} (for later cleanup)")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
