const {test} = require('node:test');
const assert = require('node:assert/strict');
const {ActivityMonitor} = require('../activity.js');
const rule = (packets, extra={}) => ({kind:'allow', source:'10.0.0.1', packets, duration_s:5, ...extra});
const state = (sampled_at, rules=[], events=[], extra={}) => ({sampled_at, rules, events, mode:'live', switch_ok:true, ...extra});

test('opening and cached samples never replay old packets or log entries', () => {
  const monitor = new ActivityMonitor();
  const sample = state('one', [rule(80)], [{event:'LOGIN_SUCCESS',time:'old',source:'10.0.0.1'}]);
  assert.deepEqual(monitor.update(sample), []);
  assert.deepEqual(monitor.update(sample), []);
});

test('a live rule delta uses its observed source and exact aggregate count', () => {
  const monitor = new ActivityMonitor();
  monitor.update(state('one', [rule(80)]));
  assert.deepEqual(monitor.update(state('two', [rule(84,{duration_s:7})])),
    [{kind:'service',source:'10.0.0.1',count:4}]);
});

test('drop counters never invent a client identity', () => {
  const monitor = new ActivityMonitor();
  monitor.update(state('one', [rule(4,{kind:'deny',source:null})]));
  assert.deepEqual(monitor.update(state('two', [rule(7,{kind:'deny',source:null,duration_s:7})])),
    [{kind:'drop',source:null,count:3}]);
});

test('replaced flow counts start at zero instead of subtracting another generation', () => {
  const monitor = new ActivityMonitor();
  monitor.update(state('one', [rule(80,{duration_s:50})]));
  assert.deepEqual(monitor.update(state('two', [rule(3,{duration_s:1})])),
    [{kind:'service',source:'10.0.0.1',count:3}]);
});

test('counter decreases do not create negative or fictional activity', () => {
  const monitor = new ActivityMonitor();
  monitor.update(state('one', [rule(80)]));
  assert.deepEqual(monitor.update(state('two', [rule(4,{duration_s:7})])), []);
});

test('new log entries animate once while retained history stays quiet', () => {
  const monitor = new ActivityMonitor();
  const old = {event:'LOGIN_SUCCESS',time:'old',source:'10.0.0.1'};
  const fresh = {event:'LOGIN_FAILURE',time:'new',source:'10.0.0.2',count:1};
  monitor.update(state('one', [], [old]));
  assert.deepEqual(monitor.update(state('two', [], [fresh,old])), [{kind:'event',event:fresh}]);
  assert.deepEqual(monitor.update(state('three', [], [fresh,old])), []);
});

test('recorded files do not produce automatic live activity', () => {
  const monitor = new ActivityMonitor();
  monitor.update(state('one',[rule(1)]));
  assert.deepEqual(monitor.update(state('two',[rule(30)],[],{mode:'recorded'})), []);
});

test('reconnection starts a new baseline instead of animating an unseen interval', () => {
  const monitor = new ActivityMonitor();
  monitor.update(state('one',[rule(1)]));
  monitor.update(state('two',[],[],{switch_ok:false}));
  assert.deepEqual(monitor.update(state('three',[rule(80)])), []);
});
