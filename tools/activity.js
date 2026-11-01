/* Observation changes only: no traffic generation, timers or invented packets. */
(function (root) {
  'use strict';
  const eventKey = event => JSON.stringify(event);
  const ruleKey = rule => `${rule.kind}:${rule.source || 'unattributed'}`;

  class ActivityMonitor {
    constructor() { this.reset(); }

    reset() {
      this.previous = null;
      this.seenEvents = new Set();
    }

    update(state) {
      if (state.mode !== 'live' || !state.switch_ok) {
        this.reset();
        return [];
      }
      const keys = state.events.map(eventKey);
      if (!this.previous) {
        this.previous = state;
        keys.forEach(key => this.seenEvents.add(key));
        return []; // Opening a page must not animate old counters or log history.
      }
      if (this.previous.sampled_at === state.sampled_at) return [];
      const activity = [];
      const oldRules = new Map(this.previous.rules.map(rule => [ruleKey(rule), rule]));
      for (const rule of state.rules) {
        const old = oldRules.get(ruleKey(rule));
        const replaced = old && rule.duration_s < old.duration_s;
        const delta = old && !replaced ? rule.packets - old.packets : rule.packets;
        if (Number.isSafeInteger(delta) && delta > 0) {
          activity.push({kind: rule.kind === 'allow' ? 'service' : 'drop',
                         source: rule.kind === 'allow' ? rule.source : null, count: delta});
        }
      }
      // Reverse newest-first log entries so new events retain their observed order.
      for (const event of [...state.events].reverse()) {
        const key = eventKey(event);
        if (!this.seenEvents.has(key)) activity.push({kind: 'event', event});
        this.seenEvents.add(key);
      }
      while (this.seenEvents.size > 512) this.seenEvents.delete(this.seenEvents.values().next().value);
      this.previous = state;
      return activity;
    }
  }

  const api = {ActivityMonitor};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.SDNActivity = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
