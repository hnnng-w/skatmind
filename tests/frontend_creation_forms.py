"""Returned-form setup submission shared by existing HTTP workflow regressions."""

from urllib.parse import urlencode


def submit_reviewed_creation(request, server, headers, route, values):
    from test_session_recorded_review_web import Forms

    page_route = "/sessions" if route == "/sessions/create" else "/matches/new"
    headers = {**headers, "Content-Type": "application/x-www-form-urlencoded"}
    status, _, body = request(server, "GET", page_route, headers=headers)
    assert status == 200
    form = Forms(body.decode()).find(route)
    response = request(server, "POST", route, headers=headers, body=urlencode({
        **form["values"], **values, "setup_action": "update"}).encode("ascii"))
    if response[0] != 303:
        return response
    status, _, body = request(server, "GET", page_route, headers=headers)
    assert status == 200
    form = Forms(body.decode()).find(route)
    return request(server, "POST", route, headers=headers, body=urlencode({
        **form["values"], "setup_action": "create"}).encode("ascii"))


def new_name_roster():
    return {"perspective_mode": "manual", "own_seat": "",
            **{f"{seat}_mode": "new" for seat in ("forehand", "middlehand", "rearhand")},
            "forehand_name": "Alice", "middlehand_name": "Bob", "rearhand_name": "Carol"}
