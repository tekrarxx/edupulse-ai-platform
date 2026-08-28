"""Seeds one real Physics slice: Mekanik -> Kuvvet -> Newton'un Hareket
Yasaları (§19 Phase 3 requirement). Idempotent — safe to run against a
database that already has this data; it skips instead of duplicating.

`learning_outcome_code` is left unset here rather than invented: mapping to
the actual MEB/Türkiye Yüzyılı Maarif Modeli outcome codes needs the real
curriculum documents, and a fabricated code would misrepresent official
content (§105 — no fake data presented as real).

Run: `python -m scripts.seed_curriculum` (inside the api container/venv).
"""
from app.db.session import SessionLocal
from app.models.curriculum import Concept, Prerequisite, Skill, SkillFacet, SkillFacetType, Subject, Topic


def seed() -> None:
    db = SessionLocal()
    try:
        subject = db.query(Subject).filter(Subject.slug == "fizik").first()
        if subject is None:
            subject = Subject(slug="fizik", name="Fizik")
            db.add(subject)
            db.flush()

        topic = db.query(Topic).filter(Topic.subject_id == subject.id, Topic.slug == "mekanik").first()
        if topic is None:
            topic = Topic(subject_id=subject.id, slug="mekanik", name="Mekanik")
            db.add(topic)
            db.flush()

        concept = db.query(Concept).filter(Concept.topic_id == topic.id, Concept.slug == "kuvvet").first()
        if concept is None:
            concept = Concept(topic_id=topic.id, slug="kuvvet", name="Kuvvet")
            db.add(concept)
            db.flush()

        newton_1 = db.query(Skill).filter(Skill.concept_id == concept.id, Skill.slug == "newton-1-yasasi").first()
        if newton_1 is None:
            newton_1 = Skill(
                concept_id=concept.id,
                slug="newton-1-yasasi",
                name="Newton'un Birinci Hareket Yasası (Eylemsizlik)",
                description="Bir cisme etki eden net kuvvet sıfırsa, cismin hareket durumu değişmez.",
                grade_level=9,
            )
            db.add(newton_1)
            db.flush()

        newton_2 = db.query(Skill).filter(Skill.concept_id == concept.id, Skill.slug == "newton-2-yasasi").first()
        if newton_2 is None:
            newton_2 = Skill(
                concept_id=concept.id,
                slug="newton-2-yasasi",
                name="Newton'un İkinci Hareket Yasası",
                description="Bir cismin ivmesi, üzerine etki eden net kuvvetle doğru, kütlesiyle ters orantılıdır (F = m·a).",
                grade_level=9,
            )
            db.add(newton_2)
            db.flush()

        existing_facets = {f.facet_type for f in db.query(SkillFacet).filter(SkillFacet.skill_id == newton_2.id).all()}
        facet_descriptions = {
            SkillFacetType.RECOGNITION: "F = m·a formülünü ve değişkenlerini tanır.",
            SkillFacetType.RECALL: "Kuvvet, kütle ve ivme arasındaki ilişkiyi hatırlar.",
            SkillFacetType.APPLICATION: "Verilen kuvvet ve kütle değerleriyle ivmeyi hesaplar.",
            SkillFacetType.TRANSFER: "Sürtünmeli yüzey veya eğik düzlem gibi tanıdık olmayan bir bağlamda F = m·a'yı uygular.",
            SkillFacetType.RETENTION: "14 veya 28 gün sonra F = m·a'yı yeniden doğru uygular.",
        }
        for facet_type, description in facet_descriptions.items():
            if facet_type not in existing_facets:
                db.add(SkillFacet(skill_id=newton_2.id, facet_type=facet_type, description=description))

        existing_prereq = (
            db.query(Prerequisite)
            .filter(Prerequisite.skill_id == newton_2.id, Prerequisite.prerequisite_skill_id == newton_1.id)
            .first()
        )
        if existing_prereq is None:
            db.add(Prerequisite(skill_id=newton_2.id, prerequisite_skill_id=newton_1.id))

        db.commit()
        print(f"Seeded: {subject.name} > {topic.name} > {concept.name} > {newton_1.name}, {newton_2.name}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
