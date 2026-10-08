"""Read-only lookup for the complete AIGC creative assistant library."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote

def emit(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))

def digest(data):
    return hashlib.sha256(data).hexdigest().upper()

def within(root, relative):
    path=(root/str(relative).replace('\\','/')).resolve()
    if not path.is_relative_to(root):
        raise ValueError('文件路径超出资料库')
    return path

def load(root_arg):
    skill_root=Path(__file__).resolve().parent.parent
    config=json.loads((skill_root/'references/library_config.json').read_text(encoding='utf-8-sig'))
    root=Path(root_arg).resolve() if root_arg else within(skill_root,config['root'])
    if not root.is_dir():
        raise FileNotFoundError(f'资料库不可访问：{root}；可使用--root覆盖位置')
    index_path=within(root,config['index'])
    if not index_path.is_file():
        raise FileNotFoundError('工作索引缺失；请读取00_分类导航.md和原TXT，不能声称已查阅工作库')
    index=json.loads(index_path.read_text(encoding='utf-8-sig'))
    return root,index

def library(index,number):
    entries=[x for x in index['Libraries'] if x['Id']==number]
    if len(entries)!=1:
        raise ValueError(f'库号{number}不存在或不唯一')
    return entries[0]

def module(index,name):
    entries=[x for x in index['Modes'] if x['id']==name or x['name']==name]
    if len(entries)!=1:
        raise ValueError(f'咨询模块{name}不存在或不唯一')
    return entries[0]

def raw_text(path):
    with path.open(encoding='utf-8-sig',newline='') as handle:
        return handle.read()

def metadata(item):
    omitted={'Topics','DeepExpansions','OriginalBlockOffset','OriginalCharacterCount','OriginalTextSHA256',
             'CurrentWorkflowChoices','ConditionalWorkflowChoices','AuxiliaryDeepChoices',
             'CurrentDelivery','CurrentHandoff'}
    result={key:value for key,value in item.items() if key not in omitted}
    # Route/catalog locate resources; the module contains full rules and positions.
    # Do not repeat every resource path and handoff for each route candidate.
    if 'CurrentWorkflowChoices' in item:
        result['CurrentWorkflowTaskIds']=list(dict.fromkeys(
            task for choice in item['CurrentWorkflowChoices'] for task in choice['TaskIds']))
        result['ConditionalHistoryIds']=list(dict.fromkeys(
            choice['HistoryId'] for choice in item.get('ConditionalWorkflowChoices',[])))
        result['AuxiliaryTaskIds']=[choice['TaskId'] for choice in item.get('AuxiliaryDeepChoices',[])]
    return result

def deep_text(text, section):
    start=section['Offset'];end=start+section['CharacterCount']
    segment=text[start:end]
    if start<0 or end>len(text) or digest(segment.encode('utf-8'))!=section['SHA256']:
        raise ValueError('深度段落偏移或哈希不符：'+section['TaskId']+'；请刷新索引')
    return segment

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',help='资料库根目录，临时覆盖配置')
    sub=parser.add_subparsers(dest='command',required=True)
    catalog=sub.add_parser('catalog')
    catalog.add_argument('--kind',choices=['modules','libraries','workflows','history','all'],default='modules')
    route=sub.add_parser('route')
    route.add_argument('--query',required=True)
    route.add_argument('--limit',type=int,default=4)
    search=sub.add_parser('search')
    search.add_argument('--query',required=True)
    search.add_argument('--library',type=int,action='append')
    search.add_argument('--scope',choices=['libraries','workflows','history','all'],default='libraries')
    search.add_argument('--limit',type=int,default=10)
    read=sub.add_parser('read')
    target=read.add_mutually_exclusive_group(required=True)
    target.add_argument('--library',type=int)
    target.add_argument('--module')
    target.add_argument('--file')
    read.add_argument('--start',type=int,default=1)
    read.add_argument('--count',type=int,default=160)
    term=sub.add_parser('term')
    term.add_argument('--library',type=int,required=True)
    term.add_argument('--ordinal',type=int,required=True)
    term.add_argument('--layer',choices=['original','deep','both'],default='both')
    deep=sub.add_parser('deep',help='按稳定任务ID读取深度段落')
    deep.add_argument('--task',required=True)
    sub.add_parser('validate')
    args=parser.parse_args()
    root,index=load(args.root)
    if args.command=='catalog':
        result={'Coverage':index['Coverage']}
        if args.kind in ('modules','all'):
            result['Modules']=[metadata(x) for x in index['Modes']]
        if args.kind in ('libraries','all'):
            result['Libraries']=[metadata(x) for x in index['Libraries']]
        if args.kind in ('workflows','all'):
            result['WorkflowSources']=[metadata(x) for x in index['SourceDocuments']]
        if args.kind in ('history','all'):
            result['HistoricalPrompts']=index.get('HistoricalPrompts',[])
        emit(result)
    elif args.command=='route':
        if not args.query.strip() or args.limit<1:
            raise ValueError('查询不能为空，limit必须大于零')
        query=args.query.casefold()
        results=[]
        for item in index['Modes']:
            matches=[keyword for keyword in item['keywords'] if keyword.casefold() in query]
            score=sum(len(keyword)**2 for keyword in matches)
            if item['name'].casefold() in query:
                score+=100
            if score:
                results.append({**metadata(item),'MatchedKeywords':matches,'MatchScore':score})
        results.sort(key=lambda item:-item['MatchScore'])
        emit({'Query':args.query,'Candidates':results[:args.limit],
              'AvailableModules':[] if results else [{'id':x['id'],'name':x['name']} for x in index['Modes']],
              'Note':'匹配是辅助定位；根据当前目标选择主模块，不自动执行所有候选。'})
    elif args.command=='read':
        if args.start<1 or args.count<1:
            raise ValueError('start和count必须大于零')
        item=library(index,args.library) if args.library is not None else module(index,args.module) if args.module else None
        relative=item['ExpandedRelativePath'] if item else args.file
        text=raw_text(within(root,relative))
        if item and item.get('ExpandedSHA256') and digest(text.encode('utf-8'))!=item['ExpandedSHA256']:
            print('提示：MD已变化，以下是当前内容；词条偏移索引需要更新。',file=sys.stderr)
        lines=text.splitlines()
        if args.start>len(lines):
            raise ValueError(f'起始行超界；选中文件共{len(lines)}行')
        end=min(args.start+args.count-1,len(lines))
        print(f'来源：{relative}；行{args.start}—{end}，共{len(lines)}行。原文层和扩写层须分别辨认。')
        for number in range(args.start,end+1):
            print(f'{number}: {lines[number-1]}')
        if end<len(lines):
            print(f'继续读取：--start {end+1} --count {args.count}')
    elif args.command=='term':
        item=library(index,args.library)
        topics=item['Topics']
        if args.ordinal<1 or args.ordinal>len(topics):
            raise ValueError(f'词条出现序号超界，本库索引共{len(topics)}项')
        text=raw_text(within(root,item['ExpandedRelativePath']))
        if digest(text.encode('utf-8'))!=item['ExpandedSHA256']:
            raise ValueError('MD已变化，不能依旧偏移读取词条；请用search/read定位当前内容并更新索引')
        original=text[item['OriginalBlockOffset']:item['OriginalBlockOffset']+item['OriginalCharacterCount']]
        selected=topics[args.ordinal-1]
        end=topics[args.ordinal]['SourceOffset'] if args.ordinal<len(topics) else len(original)
        print(f'来源：库{args.library:02d} {item["Name"]}；出现序号{args.ordinal}；原编号{selected["OriginalNumber"]}；{selected["Title"]}')
        if args.layer in ('original','both'):
            print('原文层：')
            print(original[selected['SourceOffset']:end])
        task=f'L{args.library:02d}-T{args.ordinal:04d}'
        section=next((x for x in item.get('DeepExpansions',[]) if x['TaskId']==task),None)
        if args.layer in ('deep','both'):
            if section:
                print(f'深度扩写层：{task}；MD行{section["Line"]}。文本设计与自审不代表实际生成验证。')
                print(deep_text(text,section))
            else:
                print(f'深度扩写层：{task}尚无已接入段落；请读本库应用层，不能视为逐条完成。')
        print('按当前目标应用；原文事实、AI设计值与实际生成验证分开辨认。')
    elif args.command=='deep':
        matches=[(item,section) for item in index['Libraries']+index.get('SourceDocuments',[])
                 for section in item.get('DeepExpansions',[]) if section['TaskId']==args.task]
        if len(matches)!=1:raise ValueError('深度任务未接入或不唯一：'+args.task)
        item,section=matches[0]
        text=raw_text(within(root,item['ExpandedRelativePath']))
        if digest(text.encode('utf-8'))!=item['ExpandedSHA256']:
            raise ValueError('MD已变化，不能依旧偏移读取深度段落；请用search/read定位并更新索引')
        print(f'来源：{item["ExpandedRelativePath"]}；任务{args.task}；行{section["Line"]}。文本自审，非生成效果验证。')
        print(deep_text(text,section))
    elif args.command=='search':
        if args.limit<1 or not args.query.strip():
            raise ValueError('查询不能为空，limit必须大于零')
        keywords=args.query.casefold().split()
        if args.library and args.scope not in ('libraries','all'):
            raise ValueError('--library只能与libraries/all范围配合')
        selected=[library(index,n) for n in args.library] if args.library else index['Libraries'] if args.scope in ('libraries','all') else []
        if args.scope in ('workflows','all'):
            selected=selected+index['SourceDocuments']
        if args.scope in ('history','all'):
            selected=selected+index.get('HistoricalPrompts',[])
        results=[]
        for item in selected:
            path=within(root,item['ExpandedRelativePath'])
            for line_number,line in enumerate(raw_text(path).splitlines(),1):
                if all(word in line.casefold() for word in keywords):
                    results.append({'LibraryId':item.get('Id'),'SourceId':item.get('SourceId'),'HistoryId':item.get('HistoryId'),'LibraryName':item['Name'],'RelativePath':item['ExpandedRelativePath'],'Line':line_number,'Text':line})
                    if len(results)>=args.limit:
                        break
            if len(results)>=args.limit:
                break
        emit({'Query':args.query,'Results':results,'Note':'结果可能受limit限制；用read阅读前后原文及本库扩写层。'})
    elif args.command=='validate':
        errors=[]
        warnings=[]
        doc_count=0
        link_count=0
        for item in index['SourceDocuments']+index['Libraries']:
            path=within(root,item['ExpandedRelativePath'])
            if not path.is_file():
                errors.append('扩写文件缺失：'+str(path));continue
            text=raw_text(path)
            if digest(text.encode('utf-8'))!=item['ExpandedSHA256']:
                warnings.append('扩写文件已变化：'+item['ExpandedRelativePath'])
                continue
            original=text[item['OriginalBlockOffset']:item['OriginalBlockOffset']+item['OriginalCharacterCount']]
            if digest(original.encode('utf-8'))!=item['OriginalTextSHA256']:
                errors.append('原文保留块不同：'+item['ExpandedRelativePath'])
            seen=set()
            for section in item.get('DeepExpansions',[]):
                if section['TaskId'] in seen:errors.append('重复深度ID：'+section['TaskId'])
                seen.add(section['TaskId'])
                try:
                    segment=deep_text(text,section)
                    if not segment.startswith('### '+section['TaskId']+'｜'):
                        errors.append('深度段落标题不符：'+section['TaskId'])
                    if section['Line']!=text.count('\n',0,section['Offset'])+1:
                        errors.append('深度段落行号不符：'+section['TaskId'])
                    if item['OriginalBlockOffset']<=section['Offset']<item['OriginalBlockOffset']+item['OriginalCharacterCount']:
                        errors.append('深度段落落入原文层：'+section['TaskId'])
                except ValueError as error:errors.append(str(error))
            if 'OriginalRelativePath' in item:
                source=within(root,item['OriginalRelativePath'])
                if not source.is_file():errors.append('原TXT缺失：'+str(source))
                elif digest(source.read_bytes())!=item['OriginalSHA256']:
                    warnings.append('原TXT已更新：'+item['OriginalRelativePath'])
            doc_count+=1
        for item in index['Modes']:
            path=within(root,item['ExpandedRelativePath'])
            if not path.is_file():errors.append('咨询模块缺失：'+str(path))
            for target in item['WorkflowExpandedPaths']:
                if not within(root,target).is_file():errors.append('工作流引用缺失：'+target)
        for item in index.get('HistoricalPrompts',[]):
            path=within(root,item['ExpandedRelativePath'])
            if not path.is_file():errors.append('历史提示词缺失：'+str(path))
            elif digest(path.read_bytes())!=item['ImportedSHA256']:warnings.append('历史提示词已变化：'+item['ExpandedRelativePath'])
        working=within(root,'91_创作小秘工作库')
        original_spans={within(root,item['ExpandedRelativePath']):item for item in index['SourceDocuments']+index['Libraries']}
        for path in working.rglob('*.md'):
            text=raw_text(path)
            # Only authored Markdown links live outside literal original blocks.
            item=original_spans.get(path.resolve())
            if item:
                start=item['OriginalBlockOffset']
                end=start+item['OriginalCharacterCount']
                text=text[:start]+text[end:]
            for match in re.finditer(r'\]\(([^)]+)\)',text):
                target=unquote(match[1])
                if re.match(r'https?://',target):continue
                target_path=(path.parent/target).resolve()
                link_count+=1
                if not target_path.is_relative_to(root) or not target_path.exists():
                    errors.append('链接缺失或越界：'+str(path)+' -> '+target)
        emit({'CheckedOriginalBlocks':doc_count,'Modes':len(index['Modes']),'Libraries':len(index['Libraries']),'HistoricalPrompts':len(index.get('HistoricalPrompts',[])),'CheckedLinks':link_count,'Errors':errors,'Warnings':warnings,
              'Scope':'仅验证文件、原文保留和引用；不代表内容科学准确或模型效果已验证。'})
        if errors:return 1
    return 0

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
    try:
        sys.exit(main())
    except (OSError,ValueError,KeyError,TypeError) as error:
        print('检索失败：'+str(error),file=sys.stderr)
        sys.exit(2)
