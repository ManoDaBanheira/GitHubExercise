from copy import deepcopy
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

import src.app as app_module


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "activities", deepcopy(app_module.activities))
    with TestClient(app_module.app) as test_client:
        yield test_client


def activity_url(activity_name):
    return quote(activity_name, safe="")


def test_root_redirects_to_frontend(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_seed_data(client):
    response = client.get("/activities")

    assert response.status_code == 200
    assert "Chess Club" in response.json()
    assert response.json()["Chess Club"]["participants"] == [
        "michael@mergington.edu",
        "daniel@mergington.edu",
    ]


def test_signup_adds_participant(client):
    activity_name = "Soccer Team"
    email = "new.student@mergington.edu"

    response = client.post(
        f"/activities/{activity_url(activity_name)}/signup", params={"email": email}
    )

    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for {activity_name}"}
    assert email in client.get("/activities").json()[activity_name]["participants"]


def test_signup_rejects_duplicate_email(client):
    activity_name = "Soccer Team"
    email = "duplicate.student@mergington.edu"
    url = f"/activities/{activity_url(activity_name)}/signup"

    first = client.post(url, params={"email": email})
    second = client.post(url, params={"email": email})

    assert first.status_code == 200
    assert second.status_code == 400
    assert second.json()["detail"] == "Student is already signed up for this activity"
    assert client.get("/activities").json()[activity_name]["participants"].count(email) == 1


@pytest.mark.parametrize("email", ["", "   "])
def test_signup_rejects_empty_email(client, email):
    response = client.post(
        "/activities/Chess%20Club/signup", params={"email": email}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Email is required"


def test_signup_rejects_unknown_activity(client):
    response = client.post(
        "/activities/Unknown%20Club/signup", params={"email": "student@mergington.edu"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_rejects_full_activity(client):
    activity = app_module.activities["Soccer Team"]
    activity["participants"] = [f"student{index}@mergington.edu" for index in range(activity["max_participants"])]

    response = client.post(
        "/activities/Soccer%20Team/signup", params={"email": "new.student@mergington.edu"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Activity is full"
    assert len(activity["participants"]) == activity["max_participants"]


def test_unregister_removes_participant(client):
    activity_name = "Chess Club"
    email = "michael@mergington.edu"

    response = client.delete(
        f"/activities/{activity_url(activity_name)}/signup", params={"email": email}
    )

    assert response.status_code == 200
    assert response.json() == {"message": f"Unregistered {email} from {activity_name}"}
    assert email not in client.get("/activities").json()[activity_name]["participants"]


def test_unregister_rejects_missing_participant(client):
    response = client.delete(
        "/activities/Chess%20Club/signup", params={"email": "unknown@mergington.edu"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"


def test_unregister_rejects_unknown_activity(client):
    response = client.delete(
        "/activities/Unknown%20Club/signup", params={"email": "student@mergington.edu"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"