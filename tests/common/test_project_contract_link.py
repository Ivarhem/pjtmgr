"""ProjectContractLink 서비스 테스트."""
import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.common.models.project_contract_link import ProjectContractLink
from app.modules.common.models.user import User
from app.modules.common.schemas.project_contract_link import ProjectContractLinkCreate
from app.modules.common.services import project_contract_link as svc
from app.modules.infra.models.project import Project
from app.modules.accounting.models.contract import Contract


def _make_admin(db: Session, admin_role_id: int) -> User:
    """관리자 유저 생성."""
    user = User(
        username="admin_pcl",
        email="admin_pcl@test.com",
        hashed_password="x",
        role_id=admin_role_id,
    )
    db.add(user)
    db.flush()
    return user


def _make_normal_user(db: Session, user_role_id: int) -> User:
    """일반 유저 생성."""
    user = User(
        username="normal_pcl",
        email="normal_pcl@test.com",
        hashed_password="x",
        role_id=user_role_id,
    )
    db.add(user)
    db.flush()
    return user


def _make_project(db: Session, name: str = "테스트 프로젝트") -> Project:
    project = Project(name=name)
    db.add(project)
    db.flush()
    return project


def _make_contract(db: Session, code: str = "C-001") -> Contract:
    contract = Contract(
        contract_name="테스트 계약",
        contract_code=code,
        contract_type="SI",
        stage="계약완료",
        created_by=1,
    )
    db.add(contract)
    db.flush()
    return contract


class TestLinkProjectContract:
    def test_create_link(
        self, db_session: Session, admin_role_id: int
    ) -> None:
        admin = _make_admin(db_session, admin_role_id)
        project = _make_project(db_session)
        contract = _make_contract(db_session)
        db_session.commit()

        payload = ProjectContractLinkCreate(
            project_id=project.id, contract_id=contract.id
        )
        result = svc.link_project_contract(db_session, payload, admin)

        assert result.project_id == project.id
        assert result.contract_id == contract.id
        assert result.is_primary is False
        assert result.project_name == project.name
        assert result.contract_code == contract.contract_code

    def test_duplicate_raises(
        self, db_session: Session, admin_role_id: int
    ) -> None:
        admin = _make_admin(db_session, admin_role_id)
        project = _make_project(db_session)
        contract = _make_contract(db_session)
        db_session.commit()

        payload = ProjectContractLinkCreate(
            project_id=project.id, contract_id=contract.id
        )
        svc.link_project_contract(db_session, payload, admin)

        with pytest.raises(DuplicateError):
            svc.link_project_contract(db_session, payload, admin)

    def test_non_admin_raises(
        self, db_session: Session, user_role_id: int
    ) -> None:
        user = _make_normal_user(db_session, user_role_id)
        db_session.commit()

        payload = ProjectContractLinkCreate(project_id=1, contract_id=1)
        with pytest.raises(PermissionDeniedError):
            svc.link_project_contract(db_session, payload, user)


class TestUnlink:
    def test_unlink(
        self, db_session: Session, admin_role_id: int
    ) -> None:
        admin = _make_admin(db_session, admin_role_id)
        project = _make_project(db_session)
        contract = _make_contract(db_session)
        db_session.commit()

        payload = ProjectContractLinkCreate(
            project_id=project.id, contract_id=contract.id
        )
        link = svc.link_project_contract(db_session, payload, admin)
        svc.unlink(db_session, link.id, admin)

        assert db_session.get(ProjectContractLink, link.id) is None

    def test_unlink_not_found(
        self, db_session: Session, admin_role_id: int
    ) -> None:
        admin = _make_admin(db_session, admin_role_id)
        db_session.commit()

        with pytest.raises(NotFoundError):
            svc.unlink(db_session, 99999, admin)

    def test_unlink_non_admin_raises(
        self, db_session: Session, user_role_id: int
    ) -> None:
        user = _make_normal_user(db_session, user_role_id)
        db_session.commit()

        with pytest.raises(PermissionDeniedError):
            svc.unlink(db_session, 1, user)


class TestListByProject:
    def test_list_by_project(
        self, db_session: Session, admin_role_id: int
    ) -> None:
        admin = _make_admin(db_session, admin_role_id)
        project = _make_project(db_session)
        c1 = _make_contract(db_session, "C-010")
        c2 = _make_contract(db_session, "C-011")
        db_session.commit()

        svc.link_project_contract(
            db_session,
            ProjectContractLinkCreate(
                project_id=project.id, contract_id=c1.id, is_primary=True
            ),
            admin,
        )
        svc.link_project_contract(
            db_session,
            ProjectContractLinkCreate(
                project_id=project.id, contract_id=c2.id
            ),
            admin,
        )

        results = svc.list_by_project(db_session, project.id)
        assert len(results) == 2
        # primary가 먼저
        assert results[0].is_primary is True


class TestListByContract:
    def test_list_by_contract(
        self, db_session: Session, admin_role_id: int
    ) -> None:
        admin = _make_admin(db_session, admin_role_id)
        p1 = _make_project(db_session, "프로젝트1")
        p2 = _make_project(db_session, "프로젝트2")
        contract = _make_contract(db_session)
        db_session.commit()

        svc.link_project_contract(
            db_session,
            ProjectContractLinkCreate(
                project_id=p1.id, contract_id=contract.id
            ),
            admin,
        )
        svc.link_project_contract(
            db_session,
            ProjectContractLinkCreate(
                project_id=p2.id, contract_id=contract.id
            ),
            admin,
        )

        results = svc.list_by_contract(db_session, contract.id)
        assert len(results) == 2
