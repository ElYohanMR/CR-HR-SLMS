from urllib.parse import urlsplit, parse_qs, unquote
from PySide6.QtWidgets import QDialog
import pytest
from slms.mail_preview import MailPreview, mailto_url, original_draft
from slms.setup import login_form
from slms.window import Window
from slms.local import LocalStore
from test_departures import configure, assign, departure


def test_template_and_private_departure(system):
    _, client, session = system
    configure(client)
    assign(client)
    notice = client.get("/snapshot").json()["notifications"][0]
    assert session["actor"]["name"] in notice["body"]
    assert "UTC−06:00" in notice["body"] and "hr@example.com" in notice["body"]
    assert "Ubicación:" in notice["body"] and "SIMULACIÓN" not in notice["body"]
    assert notice["status"] == "simulado"
    task = departure(client)
    first = client.post("/commands", json=task).json()
    assert first["status"] == "confirmada"
    assert client.post("/commands", json=task).json() == first
    notices = [n for n in client.get("/snapshot").json()["notifications"] if n["command_id"] == task["id"]]
    assert len(notices) == 1
    assert notices[0]["recipient"] == "hr@example.com"
    assert "DETALLE INTERNO RESERVADO" not in notices[0]["body"]


def test_mailto_encoding_and_no_injected_headers():
    values = {"recipient": "a@example.com; b@example.com", "cc": "hr@example.com",
              "subject": "Asignación & revisión #1", "body": "Hola, José.\nCasillero: 0001 & edificio #2"}
    parsed = urlsplit(mailto_url(values))
    assert unquote(parsed.path) == "a@example.com,b@example.com"
    query = parse_qs(parsed.query)
    assert query["subject"] == [values["subject"]]
    assert query["body"] == [values["body"].replace("\n", "\r\n")]
    assert set(query) == {"cc", "subject", "body"}
    for field, invalid in (("recipient", "a@example.com?bcc=x@example.com"),
                           ("subject", "Hola\r\nBcc: bad@example.com"),
                           ("cc", "a@example.com\nBcc: bad@example.com"), ("recipient", "")):
        with pytest.raises(ValueError):
            mailto_url(dict(values, **{field: invalid}))


def test_preview_persists_separately_and_only_opens_draft(qtbot, system, tmp_path, monkeypatch):
    _, client, session = system
    configure(client)
    assign(client)
    monkeypatch.setattr(Window, "sync", lambda self: None)
    store = LocalStore(tmp_path / "draft.sqlite3")
    snapshot = client.get("/snapshot").json()
    store.put("snapshot", snapshot)
    w = Window({"url": "http://test"}, session, store)
    qtbot.addWidget(w)
    notice = snapshot["notifications"][0]
    view = MailPreview(w, notice)
    qtbot.addWidget(view)
    view.widgets["subject"].setText("Asunto editado")
    view.widgets["body"].setPlainText("Mensaje corregido")
    view.widgets["recipient"].setText("edited@example.com")
    calls = []
    monkeypatch.setattr("slms.mail_preview.QDesktopServices.openUrl", lambda url: calls.append(url.toString()) or True)
    view.open_mail()
    assert len(calls) == 1 and calls[0].startswith("mailto:")
    assert "envío se realiza allí" in view.status.text()
    assert client.get("/snapshot").json()["notifications"] == snapshot["notifications"]
    assert store.queue(session["actor"]["id"]) == []
    other = MailPreview(w, notice)
    qtbot.addWidget(other)
    assert other.values()["subject"] == "Asunto editado"
    assert other.values()["recipient"] == "edited@example.com"
    w.session["actor"]["id"] = "another-account"
    third = MailPreview(w, notice)
    qtbot.addWidget(third)
    assert third.values() == original_draft(notice)
    w.session["actor"]["role"] = "viewer"
    readonly = MailPreview(w, notice)
    qtbot.addWidget(readonly)
    readonly.open_mail()
    assert len(calls) == 1
    for dialog in (view, other, third, readonly):
        dialog.close()
    w.close()


def test_microsoft_login_is_reserved_not_an_auth_bypass(qtbot):
    from PySide6.QtWidgets import QPushButton
    form = login_form()
    qtbot.addWidget(form)
    button = form.findChild(QPushButton, "microsoftSignIn")
    assert button and not button.isEnabled() and not button.icon().isNull()
    assert "username" in form.widgets and "password" in form.widgets
    assert form.result() == QDialog.DialogCode.Rejected
