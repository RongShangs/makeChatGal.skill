import 'dart:io';
import 'package:gal_ai/gal_ai.dart';
import 'package:gal_protocol/gal_protocol.dart';

void check(bool condition,String message){if(!condition)throw StateError(message);}
PackageContent load(String path){
  final root=Directory(path).resolveSymbolicLinksSync().replaceAll('\\','/');
  final files=<String,String>{};
  for(final file in Directory(root).listSync(recursive:true).whereType<File>()){
    final name=file.path.replaceAll('\\','/').substring(root.length+1);
    files[name]=name.endsWith('.json')?file.readAsStringSync():'';
  }
  return PackageLoader.fromFiles(files);
}
Future<TransitionResult> leave(PackageContent p,WorldSnapshot world,String id,int visit) =>
  TransitionCoordinator(graph:p.sceneGraph!,registry:p.variableRegistry).leaveCurrent(
    sessionId:'skill-test',world:world,messages:const[],baseRevision:visit,
    provider:const MockSettlementProvider(),cursor:RuntimeCursor(storyId:id,visitId:visit));

Future<void> main(List<String> args)async{
  final daily=load(args[0]);var world=initialWorldFor(daily);var id='start';
  check(world.variables['day']==1,'New game must start day 1');
  for(var step=0;step<36;step++){
    final result=await leave(daily,world,id,step);check(result.accepted,'Transition rejected');
    id=result.nextSceneId!;world=result.world!;
    check(id==['afternoon','night','start'][step%3],'Daily route');
    check(world.variables['day']==1+(step+1)~/3,'Day increment position');
    check(world.variables['星澄好感']==50,'No-evidence settlement changed value');
  }
  final branch=load(args[1]);final initial=initialWorldFor(branch);
  final first=await leave(branch,initial,'start',0);
  check(['afternoon','detour'].contains(first.nextSceneId),'Random route target');
  final seen=<String>{};final router=TargetRouter();
  for(var seed=1;seed<80;seed++)seen.add(router.route(branch.scene('start')!.target,initial,rngState:seed)!.to);
  check(seen.length==2,'Both random branches must be reachable');
  for(final value in [59,60]){
    final changed=initial.copyWith(variables:{...initial.variables,'星澄好感':value});
    final result=await leave(branch,changed,'afternoon',value);
    check(result.nextEventId==(value<60?'海边纸条':'小小约定'),'Threshold boundary');
  }
  check(branch.scene('afternoon')!.characters.length==2,'Multi-character scene');
  final events=EventCoordinator(events:branch.eventDefs);
  final open=events.open(eventId:'小小约定',eventVisitId:1,storyVisitId:5);
  check(!events.canFinish(open),'First slide should not finish');
  final next=events.advance(open)!;
  check(events.currentFrame(next)!.image==events.currentFrame(open)!.image,'Slide image inheritance');
  check(events.finish(next).target.single.kinds.single.to=='night','Event target');
  final choice=events.finish(events.open(eventId:'海边纸条',eventVisitId:2)).choice!;
  check(choice.options.length==3,'Event choices');
  check(choice.options.any((o)=>o.target.kind=='appShell'&&o.target.to=='home'),'Home choice');
  check(choice.options.any((o)=>o.target.kind=='story'&&o.target.to=='start'),'Loop choice');
  print('PASS: actual runtime cycles, day boundaries, no-evidence settlement, random branches, thresholds, multiple actors, slide inheritance and event choices.');
}
