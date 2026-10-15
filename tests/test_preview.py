import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from client.demo import DemoService
from client.app import Window

@pytest.fixture
def service(tmp_path):
    s = DemoService(tmp_path / 'preview.sqlite'); s.preview()
    yield s
    s.close()

def test_profiles_and_persistence(tmp_path):
    path = tmp_path / 'data.sqlite'
    s = DemoService(path); s.register('AMMAR', 'Ammar', 'preview-password')
    with pytest.raises(ValueError): s.register('ammar', 'Other', 'preview-password')
    with pytest.raises(ValueError): s.login('ammar', 'wrong')
    s.send('ashna', '<b>literal text</b>'); s.close()
    s = DemoService(path); s.login('ammar', 'preview-password')
    assert s.history('ashna')[0][1] == '<b>literal text</b>'
    s.register('other', 'Other', 'preview-password')
    assert s.history('ashna') == []
    s.close()

def test_group_access_and_rejoin(service):
    gid = service.create_group('Study group', 'secret'); target = f'group:{gid}'
    service.send(target, 'Saved group history'); service.leave(gid)
    with pytest.raises(ValueError): service.history(target)
    with pytest.raises(ValueError): service.send(target, 'Denied')
    with pytest.raises(ValueError): service.join(gid, 'wrong')
    service.join(gid, 'secret')
    assert service.history(target)[0][1] == 'Saved group history'
    assert len(service.groups()) == 1

def test_message_validation(service):
    for body in (' ', 'x' * 4001):
        with pytest.raises(ValueError): service.send('ashna', body)
    with pytest.raises(ValueError): service.send('unknown', 'hello')

def test_navigation_and_keyboard(service):
    app = QApplication.instance() or QApplication([])
    w = Window(service); w.enter_preview(); w.show()
    w.show_chat('ashna'); w.composer.setPlainText('draft'); w.show_home(); w.show_chat('ashna')
    assert w.composer.toPlainText() == 'draft'
    QTest.keyClick(w.composer, Qt.Key_Return, Qt.ShiftModifier)
    assert len(service.history('ashna')) == 0
    QTest.keyClick(w.composer, Qt.Key_Return)
    assert service.history('ashna')[0][1] == 'draft'
    assert not w.composer.toPlainText()
    gid = service.create_group('Lab group'); w.show_chat(f'group:{gid}')
    assert w.target == f'group:{gid}'
    w.show_home(); assert w.target is None
    app.processEvents(); w.close()
