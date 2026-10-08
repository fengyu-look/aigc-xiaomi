"""Exercise full-domain lookup, content reading, and failure recovery boundaries."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parent.parent/'skills/film-creation-library/scripts/library_lookup.py'
ROOT=SCRIPT.parent.parent/'references/knowledge_base'
INDEX=json.loads((ROOT/'91_创作小秘工作库/00_全量检索索引.json').read_text(encoding='utf-8'))

def run(*args):
    return subprocess.run([sys.executable,'-X','utf8',str(SCRIPT),*map(str,args)],capture_output=True,text=True,encoding='utf-8')

class LookupTests(unittest.TestCase):
    def test_all_fifteen_domains_route_and_read(self):
        scenarios={
            'strategy':'我有一个AIGC短剧想法，先帮我分析创意方向',
            'outline':'想写小说，帮我分析题材和分集大纲',
            'screenplay':'把小说改编为影视剧本，忠实保留对白',
            'images':'角色三视图和小说封面图片怎样设计',
            'storyboard':'第一人称POV分镜如何安排视线与运镜',
            'video':'Seedance图生视频提示词怎样保持一致性',
            'performance':'群体动作和眼神微表情怎样设计',
            'effects':'仙侠打斗手诀法术特效设计',
            'sound':'门轴音效和脚步拟音，怎么混音和配音',
            'music':'想做一首歌曲，讨论歌词旋律和编曲，不急着生成',
            'commerce':'电商商品广告，品牌卖点如何做成详情图',
            'post':'成片复盘：剪辑转场和后期修复怎么处理',
            'advanced':'3D空间重建和虚拟制片交互怎么策划',
            'analysis':'参考视频分析，反推画面的提示词',
            'framework':'保留提示词框架，把语言库模板扩写得具体些',
        }
        self.assertEqual(set(scenarios),{m['id'] for m in INDEX['Modes']})
        for expected,query in scenarios.items():
            with self.subTest(module=expected):
                result=run('route','--query',query,'--limit',4)
                self.assertEqual(result.returncode,0,result.stderr)
                candidates=json.loads(result.stdout)['Candidates']
                self.assertIn(expected,[x['id'] for x in candidates])
                selected=next(x for x in candidates if x['id']==expected)
                self.assertTrue(selected['CurrentWorkflowTaskIds'])
                self.assertTrue(selected['ConditionalHistoryIds'])
                self.assertNotIn('CurrentWorkflowChoices',selected)
                self.assertNotIn('CurrentHandoff',selected)
                result=run('read','--module',expected,'--count',100)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn(next(m['name'] for m in INDEX['Modes'] if m['id']==expected),result.stdout)
                self.assertIn('异议',result.stdout)
                self.assertIn('当前流程选择与交接',result.stdout)
                self.assertIn('具体交付和上下游',result.stdout)
                self.assertNotIn('继续读取：',result.stdout)

    def test_terms_really_read_original_content(self):
        for library_id in (1,13,36,37,43,44,60):
            with self.subTest(library=library_id):
                item=next(x for x in INDEX['Libraries'] if x['Id']==library_id)
                topic=item['Topics'][0]
                result=run('term','--library',library_id,'--ordinal',1)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn(topic['Title'],result.stdout)
                self.assertGreater(len(result.stdout),len(topic['Title'])+100)
                self.assertIn('定义',result.stdout)

    def test_targeted_content_search(self):
        for library_id,query in ((43,'和声'),(37,'主观视点'),(36,'子午诀')):
            with self.subTest(library=library_id,query=query):
                result=run('search','--library',library_id,'--query',query,'--limit',2)
                self.assertEqual(result.returncode,0,result.stderr)
                matches=json.loads(result.stdout)['Results']
                self.assertTrue(matches)
                self.assertTrue(all(x['LibraryId']==library_id and query in x['Text'] for x in matches))

    def test_deep_lookup_returns_full_single_section_and_keeps_original(self):
        both=run('term','--library',1,'--ordinal',12)
        self.assertEqual(both.returncode,0,both.stderr)
        self.assertIn('原文层',both.stdout)
        self.assertIn('L01-T0012',both.stdout)
        self.assertIn('0.5秒内',both.stdout)
        self.assertIn('完整例子',both.stdout)
        self.assertNotIn('### L01-T0013',both.stdout)
        direct=run('deep','--task','L01-T0012')
        self.assertEqual(direct.returncode,0,direct.stderr)
        self.assertIn('0.4秒',direct.stdout)
        self.assertNotIn('原文层：',direct.stdout)
        original=run('term','--library',1,'--ordinal',12,'--layer','original')
        self.assertEqual(original.returncode,0,original.stderr)
        self.assertNotIn('### L01-T0012',original.stdout)

    def test_unwritten_deep_topic_is_not_reported_as_finished(self):
        with tempfile.TemporaryDirectory(prefix='creative-unwritten-') as directory:
            temp_root=Path(directory)
            item=json.loads(json.dumps(next(x for x in INDEX['Libraries'] if x['Id']==1)))
            body=(ROOT/item['ExpandedRelativePath']).read_bytes()
            item['ExpandedRelativePath']='partial.md'
            item['DeepExpansions']=[x for x in item['DeepExpansions'] if x['TaskId']!='L01-T0012']
            (temp_root/'partial.md').write_bytes(body)
            work=temp_root/'91_创作小秘工作库';work.mkdir()
            (work/'00_全量检索索引.json').write_text(json.dumps({'Libraries':[item]},ensure_ascii=False),encoding='utf-8')
            result=run('--root',temp_root,'term','--library',1,'--ordinal',12,'--layer','deep')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('尚无已接入段落',result.stdout)
            self.assertNotIn('### L01-T0011',result.stdout)
            missing=run('--root',temp_root,'deep','--task','L01-T0012')
            self.assertEqual(missing.returncode,2)
            self.assertIn('未接入',missing.stderr)

    def test_corrupted_deep_offset_is_rejected_even_if_document_hash_matches(self):
        with tempfile.TemporaryDirectory(prefix='creative-deep-') as directory:
            temp_root=Path(directory)
            item=json.loads(json.dumps(next(x for x in INDEX['Libraries'] if x['Id']==1)))
            body=(ROOT/item['ExpandedRelativePath']).read_bytes()
            item['ExpandedRelativePath']='deep.md'
            item['DeepExpansions'][0]['Offset']+=1
            (temp_root/'deep.md').write_bytes(body)
            work=temp_root/'91_创作小秘工作库';work.mkdir()
            (work/'00_全量检索索引.json').write_text(json.dumps({'Libraries':[item]},ensure_ascii=False),encoding='utf-8')
            result=run('--root',temp_root,'deep','--task','L01-T0001')
            self.assertEqual(result.returncode,2)
            self.assertIn('偏移或哈希不符',result.stderr)

    def test_fallback_for_unrecognized_request(self):
        result=run('route','--query','尚未描述具体创作目标')
        self.assertEqual(result.returncode,0,result.stderr)
        data=json.loads(result.stdout)
        self.assertEqual(data['Candidates'],[])
        self.assertEqual(len(data['AvailableModules']),15)

    def test_bad_paths_and_arguments_rejected(self):
        for args in (('read','--file','../outside.md'),('read','--library',999),
                     ('term','--library',43,'--ordinal',0),('search','--query',''),
                     ('read','--module','music','--start',0)):
            with self.subTest(args=args):
                result=run(*args)
                self.assertEqual(result.returncode,2)
                self.assertIn('检索失败',result.stderr)

    def test_missing_index_and_stale_offset_are_explicit(self):
        with tempfile.TemporaryDirectory(prefix='creative-lookup-') as directory:
            temp_root=Path(directory)
            result=run('--root',temp_root,'route','--query','音乐')
            self.assertEqual(result.returncode,2)
            self.assertIn('索引缺失',result.stderr)
            work=temp_root/'91_创作小秘工作库'
            work.mkdir()
            item=next(x for x in INDEX['Libraries'] if x['Id']==43).copy()
            item['ExpandedRelativePath']='modified.md'
            (temp_root/'modified.md').write_text('用户修改后的资料',encoding='utf-8')
            (work/'00_全量检索索引.json').write_text(json.dumps({'Libraries':[item]},ensure_ascii=False),encoding='utf-8')
            result=run('--root',temp_root,'term','--library',43,'--ordinal',1)
            self.assertEqual(result.returncode,2)
            self.assertIn('MD已变化',result.stderr)
            result=run('--root',temp_root,'read','--library',43,'--count',2)
            self.assertEqual(result.returncode,0)
            self.assertIn('用户修改后的资料',result.stdout)
            self.assertIn('MD已变化',result.stderr)

if __name__=='__main__':
    unittest.main(verbosity=2)
