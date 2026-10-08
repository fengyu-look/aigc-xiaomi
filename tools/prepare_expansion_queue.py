"""Prepare a lossless candidate queue; never overwrite existing writing progress."""
import argparse
import json
from pathlib import Path
import sys

def within(root,relative):
    path=(root/relative.replace('\\','/')).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('证据路径超出项目')
    return path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',type=Path)
    parser.add_argument('--check',action='store_true',help='只检查现有队列的覆盖与状态，不生成或改写')
    args=parser.parse_args()
    root=(args.project_root or Path(__file__).resolve().parent.parent).resolve()
    knowledge=root/'skills/film-creation-library/references/knowledge_base'
    index=json.loads((knowledge/'91_创作小秘工作库/00_全量检索索引.json').read_text(encoding='utf-8-sig'))
    target=root/'docs/deep_expansion_tasks.json'
    if args.check:
        board=json.loads(target.read_text(encoding='utf-8'))
        if {x['LibraryId'] for x in board['LibraryTasks']}!={x['Id'] for x in index['Libraries']}:raise ValueError('队列没有覆盖全部库')
        if {x['SourceId'] for x in board['SourceFiles']}!={x['SourceId'] for x in index['SourceDocuments']}:raise ValueError('队列没有覆盖全部源文件')
        if {x['HistoryId'] for x in board['HistoricalPrompts']}!={x['HistoryId'] for x in index.get('HistoricalPrompts',[])}:raise ValueError('历史稿覆盖不完整')
        identifiers=set();counts={'pending':0,'in_progress':0,'written':0,'reviewed':0}
        for group in board['LibraryTasks']:
            source=next(x for x in index['Libraries'] if x['Id']==group['LibraryId'])
            if group['OriginalTextSHA256']!=source['OriginalTextSHA256']:raise ValueError('原文基线改变，需审查清单')
            if len(group['Entries'])!=len(source['Topics']):raise ValueError('候选漏项；排除也需保留记录')
            for entry in group['Entries']:
                if entry['TaskId'] in identifiers:raise ValueError('重复任务ID')
                identifiers.add(entry['TaskId'])
                state=entry['Status']
                if state not in counts:raise ValueError('不支持的写作状态')
                counts[state]+=1
                decision=entry['InventoryDecision']
                if decision not in ('pending','include','exclude'):raise ValueError('不支持的清单决定')
                if decision=='exclude' and not entry['Notes'].strip():raise ValueError('排除项缺少理由')
                if state in ('written','reviewed'):
                    evidence=entry.get('Evidence')
                    if decision!='include' or not evidence or not evidence.get('Path'):raise ValueError('已写条目缺少纳入决定与证据')
                    if not within(root,evidence['Path']).is_file():raise ValueError('扩写证据文件缺失')
                    if state=='reviewed' and not evidence.get('ContentReview'):raise ValueError('已审查条目缺少内容审查记录')
        result={'CandidateSections':len(identifiers),'WritingStates':counts,'Libraries':len(board['LibraryTasks']),
                'SourceFiles':len(board['SourceFiles']),'HistoricalPrompts':len(board['HistoricalPrompts']),
                'Scope':'只检查覆盖与状态证据；不自动判断扩写质量或宣布全量完成'}
    else:
        if target.exists():raise ValueError('任务队列已存在；拒绝覆盖进度，可用--check检查')
        board={'SchemaVersion':'1.0','Scope':'全量逐条扩写与收尾验收','CountNote':'候选来自原文编号段落，实际词条需人工审查；不是已审核唯一词条总数',
               'LibraryTasks':[],'SourceFiles':[],'HistoricalPrompts':[],
               'ReadinessGates':[{'Gate':gate,'Status':'pending','Evidence':[]} for gate in
                                 ('inventory_review','deep_expansion','content_review','retrieval_integration','creative_drills_15_modes','final_checks')]}
        for source in index['Libraries']:
            group={'LibraryId':source['Id'],'Name':source['Name'],'File':source['ExpandedRelativePath'],
                   'OriginalTextSHA256':source['OriginalTextSHA256'],'InventoryStatus':'pending','Entries':[]}
            for ordinal,topic in enumerate(source['Topics'],1):
                group['Entries'].append({'TaskId':f'L{source["Id"]:02d}-T{ordinal:04d}','IndexOrdinal':ordinal,
                                         'OriginalNumber':topic['OriginalNumber'],'Title':topic['Title'],'SourceOffset':topic['SourceOffset'],
                                         'InventoryDecision':'pending','Status':'pending','Evidence':None,'Notes':''})
            board['LibraryTasks'].append(group)
        for source in index['SourceDocuments']:
            board['SourceFiles'].append({'SourceId':source['SourceId'],'Name':source['Name'],'File':source['ExpandedRelativePath'],
                                        'Kind':'版本差异核对' if source['Profile']=='知识库版本映射' else '工作流深化或资料作用审查',
                                        'Status':'pending','Evidence':None,'Notes':''})
        for source in index.get('HistoricalPrompts',[]):
            board['HistoricalPrompts'].append({'HistoryId':source['HistoryId'],'Name':source['Name'],'File':source['ExpandedRelativePath'],
                                              'Status':'pending','AdoptedFor':[],'Evidence':None,'Notes':''})
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(board,ensure_ascii=False,indent=2),encoding='utf-8',newline='')
        result={'Prepared':True,'Libraries':len(board['LibraryTasks']),'CandidateSections':sum(len(x['Entries']) for x in board['LibraryTasks']),
                'SourceFiles':len(board['SourceFiles']),'HistoricalPrompts':len(board['HistoricalPrompts'])}
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
    try:sys.exit(main())
    except (OSError,ValueError,KeyError) as error:print('队列操作失败：'+str(error),file=sys.stderr);sys.exit(2)
