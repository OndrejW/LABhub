import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from labhub import app, bcrypt, db
from labhub.lib.models import (
    Drawer,
    Log,
    LogCooperators,
    LogRemark,
    Project,
    Sample,
    Session,
    Setup,
    Structure,
    User,
)


DEMO_EMAIL = "demo@labhub.example"
DEMO_PASSWORD = "DemoLab123!"
DEMO_USERNAME = "Demo Researcher"


def demo_enabled():
    return os.environ.get("LABHUB_SEED_DEMO_DATA", "").lower() in {"1", "true", "yes"}


def get_or_create(model, defaults=None, **filters):
    instance = model.query.filter_by(**filters).first()
    if instance is None:
        instance = model(**filters, **(defaults or {}))
        db.session.add(instance)
        db.session.flush()
    return instance


def main():
    if not demo_enabled():
        print("Demo seed skipped. Set LABHUB_SEED_DEMO_DATA=true to enable it.")
        return

    with app.app_context():
        now = datetime.now()
        demo_user = get_or_create(
            User,
            username=DEMO_USERNAME,
            email=DEMO_EMAIL,
            defaults={"password": bcrypt.generate_password_hash(DEMO_PASSWORD).decode("utf-8")},
        )
        colleague = get_or_create(
            User,
            username="Demo Colleague",
            email="colleague@labhub.example",
            defaults={"password": bcrypt.generate_password_hash("DemoColleague123!").decode("utf-8")},
        )
        drawer = get_or_create(
            Drawer,
            name="Demo materials drawer",
            defaults={"number": 3, "desc": "Example storage location for the demo sample."},
        )
        sample = get_or_create(
            Sample,
            name="Demo thin film A01",
            defaults={
                "desc": "Illustrative thin-film sample used only for the public demo.",
                "attribute": "Substrate,Glass\nThickness,120 nm\n",
                "drawer": drawer,
            },
        )
        structure = get_or_create(
            Structure,
            name="Central region",
            sample_id=sample.id,
            defaults={"desc": "Reference area used for repeatable measurements.", "attribute": "Area,5 x 5 mm\n"},
        )
        setup = get_or_create(
            Setup,
            name="Demo optical bench",
            defaults={
                "desc": "Example setup with a temperature-controlled stage and optical readout.",
                "attribute": "Light source,LED\nStage temperature,25 C\n",
            },
        )
        project = get_or_create(
            Project,
            name="Demo: temperature stability study",
            defaults={
                "desc": "A fictional study demonstrating projects, sessions, measurements, notes, warnings, and analysis.",
            },
        )
        session = get_or_create(
            Session,
            name="Baseline characterization",
            project_id=project.id,
            defaults={
                "date": now - timedelta(days=2),
                "idea": "Establish a repeatable baseline before the temperature sweep.",
                "comment": "The sample was mounted and aligned using the normal lab procedure.",
                "findings": "Baseline response was stable over three repeat measurements.",
            },
        )
        readiness_project = get_or_create(
            Project,
            name="Demo: instrument readiness",
            defaults={
                "desc": "A separate fictional project showing how preparation and maintenance notes can be organized.",
            },
        )
        readiness_session = get_or_create(
            Session,
            name="Pre-run checks",
            project_id=readiness_project.id,
            defaults={
                "date": now - timedelta(days=1),
                "idea": "Confirm the demo optical bench is ready for the next experiment.",
                "comment": "Review alignment, stage movement, and the controller set point.",
                "findings": "All checks passed after the controller stabilized.",
            },
        )

        log = get_or_create(
            Log,
            name="Baseline measurement at 25 C",
            user_id=demo_user.id,
            typeOfOcc=0,
            defaults={
                "date": now - timedelta(days=2),
                "idea": "Record the reference signal before changing temperature.",
                "comment": "Three readings agreed within the expected repeatability.",
                "path": "demo-data/baseline-25c.csv",
                "attribute": "Temperature,25 C\nIntegration time,500 ms\nReplicates,3\n",
                "setup_id": setup.id,
                "sample_id": sample.id,
                "structure_id": structure.id,
                "project_id": project.id,
                "session_id": session.id,
            },
        )
        get_or_create(
            Log,
            name="Alignment note",
            user_id=demo_user.id,
            typeOfOcc=1,
            defaults={
                "date": now - timedelta(days=2, minutes=30),
                "comment": "The reference mark was centered before the first measurement.",
                "setup_id": setup.id,
                "sample_id": sample.id,
                "structure_id": structure.id,
                "project_id": project.id,
                "session_id": session.id,
                "attribute": "Operator note,Alignment verified\n",
            },
        )
        get_or_create(
            Log,
            name="Pre-run checklist",
            user_id=demo_user.id,
            typeOfOcc=1,
            defaults={
                "date": now - timedelta(days=1, hours=1),
                "comment": "Stage movement, optical alignment, and data folder naming were checked before the next run.",
                "setup_id": setup.id,
                "project_id": readiness_project.id,
                "session_id": readiness_session.id,
                "attribute": "Stage movement,Passed\nData path,Verified\n",
            },
        )
        get_or_create(
            Log,
            name="Temperature controller drift warning",
            user_id=demo_user.id,
            typeOfOcc=2,
            defaults={
                "date": now - timedelta(days=1, hours=23),
                "comment": "The controller briefly exceeded the target by 1.5 C. Measurements were paused and repeated after stabilization.",
                "setup_id": setup.id,
                "sample_id": sample.id,
                "structure_id": structure.id,
                "project_id": project.id,
                "session_id": session.id,
                "attribute": "Target temperature,40 C\nObserved peak,41.5 C\n",
            },
        )
        get_or_create(
            Log,
            name="Baseline trend analysis",
            user_id=demo_user.id,
            typeOfOcc=4,
            defaults={
                "date": now - timedelta(days=1),
                "idea": "Compare baseline repeats and assess whether the drift affected the trend.",
                "comment": "The repeated baseline values remain consistent after removing the unstable interval. Continue with the controlled sweep.",
                "path": "demo-data/baseline-analysis.ipynb",
                "project_id": project.id,
            },
        )
        get_or_create(
            LogCooperators,
            log_id=log.id,
            user_id=colleague.id,
        )
        get_or_create(
            LogRemark,
            log_id=log.id,
            user_id=colleague.id,
            defaults={"remark": "The baseline looks consistent. I would keep the same integration time for the sweep."},
        )
        db.session.commit()

    print(f"Demo data is ready. Sign in with {DEMO_EMAIL}.")


if __name__ == "__main__":
    main()
