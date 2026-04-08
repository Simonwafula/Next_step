from app.db.models import JobPost, Location, Organization
from scripts.backfill_normalized_entities import backfill_normalized_entities


def test_backfill_normalized_entities_renames_organization(db_session_factory):
    db = db_session_factory()
    org = Organization(name="Jobs at Safaricom Kenya Ltd", verified=False)
    db.add(org)
    db.commit()

    summary = backfill_normalized_entities(db, orgs_only=True)
    updated = db.query(Organization).filter(Organization.id == org.id).one()

    assert summary["organizations_renamed"] == 1
    assert updated.name == "Safaricom Kenya"


def test_backfill_normalized_entities_repoints_duplicate_organization_refs(
    db_session_factory,
):
    db = db_session_factory()
    org_a = Organization(name="Jobs at Safaricom Kenya Ltd", verified=False, sector="Tech")
    org_b = Organization(name="Safaricom Kenya", verified=False)
    db.add_all([org_a, org_b])
    db.flush()
    job = JobPost(source="rss", url="https://example.com/job/1", title_raw="Analyst", org_id=org_a.id)
    db.add(job)
    db.commit()

    summary = backfill_normalized_entities(db, orgs_only=True)
    updated_job = db.query(JobPost).filter(JobPost.id == job.id).one()
    canonical = db.query(Organization).filter(Organization.id == org_b.id).one()

    assert summary["organization_job_refs_repointed"] == 1
    assert updated_job.org_id == org_b.id
    assert canonical.sector == "Tech"


def test_backfill_normalized_entities_updates_location_fields(db_session_factory):
    db = db_session_factory()
    loc = Location(raw=" Nairobi \n Kenya ")
    db.add(loc)
    db.commit()

    summary = backfill_normalized_entities(db, locations_only=True)
    updated = db.query(Location).filter(Location.id == loc.id).one()

    assert summary["locations_updated"] == 1
    assert updated.city == "Nairobi"
    assert updated.region == "Nairobi"
    assert updated.country == "Kenya"
