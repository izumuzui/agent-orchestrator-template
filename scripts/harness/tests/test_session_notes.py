import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2] / 'session-notes'

def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

note = load('codex_note', 'codex_session_note.py')
installer = load('note_install', 'install.py')

class Notes(unittest.TestCase):
    def test_rollout_filters_and_identity(self):
        def msg(role, text, phase=None):
            return {'type':'response_item','timestamp':'2026-10-27T15:00:00Z',
                    'payload':{'type':'message','role':role,'phase':phase,
                               'content':[{'type':'input_text' if role=='user' else 'output_text','text':text}]}}
        rows = [{'type':'session_meta','payload':{'id':'abc-123'}},
                msg('user','# AGENTS.md instructions\nprivate'),msg('user','<environment_context>injected'),
                msg('user','Question'),msg('developer','private'),msg('assistant','hidden','analysis'),
                {'type':'event_msg','payload':{'type':'user_message','message':'Question'}},
                msg('assistant','Answer','final_answer'), msg('user','Followup')]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'log.jsonl'
            p.write_text('\n'.join(map(json.dumps,rows))+'\n{')
            text,title,turns,first,last=note.condense(p)
            self.assertEqual(turns,2)
            self.assertEqual(text.count('Question'),1)
            self.assertIn('Answer',text)
            self.assertNotIn('private',text)
            self.assertNotIn('hidden',text)
            self.assertEqual(note.session_id(p),'codex-abc-123')

    def test_install_preserves_hooks_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp); root=home/'.codex';root.mkdir()
            old={'hooks':{'PreToolUse':[{'hooks':[{'command':'guard'}]}]},'custom':True}
            (root/'hooks.json').write_text(json.dumps(old))
            installer.install(home);installer.install(home)
            new=json.loads((root/'hooks.json').read_text())
            self.assertEqual(new['hooks']['PreToolUse'],old['hooks']['PreToolUse'])
            self.assertTrue(new['custom'])
            for event in ('Stop','SessionEnd'):
                self.assertEqual(len(new['hooks'][event]),1)
            self.assertTrue(list(root.glob('hooks.json.bak-*')))

    def test_throttle_and_end_retry(self):
        with patch.object(note,'condense',return_value=('conversation',None,2,'2026-10-27T00:00:00Z',None)), \
             patch.object(note,'load_state',return_value={'id':{'turns':2,'at':0}}), \
             patch.object(note,'summarize') as summary:
            note.write_note('unused','','id','stop')
            summary.assert_not_called()

    def test_git_failure_does_not_advance_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault=Path(tmp);sessions=vault/'sessions';projects=vault/'projects';projects.mkdir()
            with patch.multiple(note,VAULT=vault,SESSIONS=sessions,PROJECTS=projects), \
                 patch.object(note,'condense',return_value=('conversation',None,2,'2026-10-27T00:00:00Z',None)), \
                 patch.object(note,'load_state',return_value={}), \
                 patch.object(note,'summarize',return_value='SLUG: demo\nTITLE: Test\nPROJECTS:\nTAGS: test\n## Purpose\nDone'), \
                 patch.object(note,'git') as git,patch.object(note,'save_state') as save:
                git.return_value.returncode=1
                git.return_value.stdout=""
                with self.assertRaises(RuntimeError):note.write_note('unused','','id','end')
                save.assert_not_called()
                self.assertEqual(len(list(sessions.glob('*.md'))),0)

class UpdateSafety(unittest.TestCase):
    def test_end_refreshes_same_turns_changed_content(self):
        with patch.object(note,'condense',return_value=('new answer',None,2,None,None)), \
             patch.object(note,'load_state',return_value={'id':{'turns':2,'fingerprint':'old'}}), \
             patch.object(note,'summarize',side_effect=RuntimeError('reached summary')) as summary:
            with self.assertRaisesRegex(RuntimeError,'reached summary'):
                note.write_note('unused','','id','end')
            summary.assert_called_once()

    def test_dirty_project_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault=Path(tmp);sessions=vault/'sessions';projects=vault/'projects';projects.mkdir()
            project=projects/'demo.md';project.write_text('user edits')
            with patch.multiple(note,VAULT=vault,SESSIONS=sessions,PROJECTS=projects), \
                 patch.object(note,'condense',return_value=('conversation',None,2,None,None)), \
                 patch.object(note,'load_state',return_value={}), \
                 patch.object(note,'summarize',return_value='SLUG: demo\nTITLE: Test\nPROJECTS: demo\nTAGS: test\n## Purpose\nDone'), \
                 patch.object(note,'git') as git:
                git.return_value.returncode=0;git.return_value.stdout=' M projects/demo.md'
                with self.assertRaisesRegex(RuntimeError,'local edits'):
                    note.write_note('unused','','id','end')
                self.assertEqual(project.read_text(),'user edits')
                self.assertEqual(list(sessions.glob('*.md')),[])

class Lifecycle(unittest.TestCase):
    def test_successful_write_repeat_and_project_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault=Path(tmp);sessions=vault/'sessions';projects=vault/'projects';projects.mkdir()
            (projects/'demo.md').write_text('# Demo\n')
            with patch.multiple(note,VAULT=vault,SESSIONS=sessions,PROJECTS=projects,STATE=vault/'state.json'), \
                 patch.object(note,'condense',return_value=('conversation',None,2,None,None)), \
                 patch.object(note,'summarize',return_value='SLUG: demo\nTITLE: Test\nPROJECTS: demo\nTAGS: test\n## Purpose\nDone') as summary, \
                 patch.object(note,'git') as git,patch.object(note,'log'):
                git.return_value.returncode=0;git.return_value.stdout=''
                note.write_note('unused','','codex-id','end')
                note.write_note('unused','','codex-id','end')
                self.assertEqual(summary.call_count,1)
                self.assertEqual(len(list(sessions.glob('*.md'))),1)
                self.assertEqual((projects/'demo.md').read_text().count('[['),1)
                self.assertIn('fingerprint',json.loads((vault/'state.json').read_text())['codex-id'])

    def test_commit_failure_rolls_back_then_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault=Path(tmp);sessions=vault/'sessions';projects=vault/'projects';projects.mkdir()
            project=projects/'demo.md';project.write_text('# Original\n')
            class Result:
                def __init__(self,code=0):self.returncode=code;self.stdout=''
            fail = [True]
            def git_result(*args):
                if args[0]=='diff':return Result(1)
                if args[0]=='commit' and fail[0]:return Result(1)
                return Result()
            with patch.multiple(note,VAULT=vault,SESSIONS=sessions,PROJECTS=projects,STATE=vault/'state.json'), \
                 patch.object(note,'condense',return_value=('conversation',None,2,None,None)), \
                 patch.object(note,'summarize',return_value='SLUG: demo\nTITLE: Test\nPROJECTS: demo\nTAGS: test\n## Purpose\nDone'), \
                 patch.object(note,'git',side_effect=git_result),patch.object(note,'log'):
                with self.assertRaisesRegex(RuntimeError,'commit failed'):
                    note.write_note('unused','','codex-id','end')
                self.assertEqual(project.read_text(),'# Original\n')
                self.assertEqual(list(sessions.glob('*.md')),[])
                fail[0]=False
                note.write_note('unused','','codex-id','end')
                self.assertEqual(len(list(sessions.glob('*.md'))),1)

    def test_hook_dispatch(self):
        import io
        with tempfile.TemporaryDirectory() as tmp:
            transcript=Path(tmp)/'rollout.jsonl';transcript.write_text('')
            for event,mode in [('Stop','stop'),('SessionEnd','end')]:
                with patch.object(note.sys,'argv',['hook']), \
                     patch.object(note.sys,'stdin',io.StringIO(json.dumps({'transcript_path':str(transcript),'hook_event_name':event}))), \
                     patch.object(note.subprocess,'Popen') as popen,patch.dict(note.os.environ,{},clear=True):
                    note.main()
                    self.assertEqual(popen.call_args.args[0][-1],mode)

if __name__=='__main__':unittest.main()
