"""Seeds one real Chemistry slice: Kimyasal Bağlar -> İyonik Bağ (§19).
Mirrors scripts/seed_curriculum.py's Physics slice exactly — same model
calls, same idempotent pattern — deliberately, since the point of this
script existing is to demonstrate that CLAUDE.md §2's "the architecture
MUST NOT hard-code the entire system around Physics" claim is real: adding
a second subject required zero application-code changes, only new
curriculum rows through the same API/models every other subject uses.

`learning_outcome_code` left unset for the same reason as the Physics
seed — a fabricated MEB code would misrepresent official content (§105).

Run: `python -m scripts.seed_curriculum_chemistry` (inside the api
container/venv).
"""
from app.db.session import SessionLocal
from app.models.curriculum import Concept, Skill, SkillFacet, SkillFacetType, Subject, Topic


def seed() -> None:
    db = SessionLocal()
    try:
        subject = db.query(Subject).filter(Subject.slug == "kimya").first()
        if subject is None:
            subject = Subject(slug="kimya", name="Kimya")
            db.add(subject)
            db.flush()

        topic = db.query(Topic).filter(Topic.subject_id == subject.id, Topic.slug == "kimyasal-baglar").first()
        if topic is None:
            topic = Topic(subject_id=subject.id, slug="kimyasal-baglar", name="Kimyasal Bağlar")
            db.add(topic)
            db.flush()

        concept = db.query(Concept).filter(Concept.topic_id == topic.id, Concept.slug == "iyonik-bag").first()
        if concept is None:
            concept = Concept(topic_id=topic.id, slug="iyonik-bag", name="İyonik Bağ")
            db.add(concept)
            db.flush()

        skill = db.query(Skill).filter(Skill.concept_id == concept.id, Skill.slug == "iyonik-bag-olusumu").first()
        if skill is None:
            skill = Skill(
                concept_id=concept.id,
                slug="iyonik-bag-olusumu",
                name="İyonik Bağ Oluşumu",
                description="Bir metal ile bir ametal arasında elektron aktarımıyla oluşan iyonik bağı tanımlar ve örnekler.",
                grade_level=9,
            )
            db.add(skill)
            db.flush()

        existing_facets = {f.facet_type for f in db.query(SkillFacet).filter(SkillFacet.skill_id == skill.id).all()}
        facet_descriptions = {
            SkillFacetType.RECOGNITION: "İyonik bağ içeren bir bileşiği tanır (örn. NaCl).",
            SkillFacetType.RECALL: "İyonik bağın elektron aktarımıyla oluştuğunu hatırlar.",
            SkillFacetType.APPLICATION: "Verilen iki elementten hangisinin katyon, hangisinin anyon olacağını belirler.",
            SkillFacetType.TRANSFER: "Tanıdık olmayan bir element çiftinde iyonik bağ oluşup oluşmayacağını çıkarır.",
            SkillFacetType.RETENTION: "14 veya 28 gün sonra iyonik bağ oluşumunu yeniden doğru belirler.",
        }
        for facet_type, description in facet_descriptions.items():
            if facet_type not in existing_facets:
                db.add(SkillFacet(skill_id=skill.id, facet_type=facet_type, description=description))

        db.commit()
        print(f"Seeded: {subject.name} > {topic.name} > {concept.name} > {skill.name}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
