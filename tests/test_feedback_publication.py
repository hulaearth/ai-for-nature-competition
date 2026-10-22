import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('feedback',ROOT/'scripts/publish_feedback.py')
feedback=importlib.util.module_from_spec(spec);spec.loader.exec_module(feedback)

class FeedbackPublication(unittest.TestCase):
    def test_only_sanitized_public_documents_are_allowed(self):
        docs=feedback.documents()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'site').mkdir()
            for name,value in docs.items():(root/'site'/name).write_text(json.dumps(value))
            self.assertEqual(feedback.documents(root),docs)
            broken=copy.deepcopy(docs['receipts.json']);broken['teams']=[{'members':['private nickname']}]
            (root/'site/receipts.json').write_text(json.dumps(broken))
            with self.assertRaisesRegex(RuntimeError,'Private field'):feedback.documents(root)
            broken['teams']=[];broken['competition']='synthetic-pilot'
            (root/'site/receipts.json').write_text(json.dumps(broken))
            with self.assertRaisesRegex(RuntimeError,'destination'):feedback.documents(root)
