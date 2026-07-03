/**
 * MunninAI — Application JavaScript
 *
 * Alpine.js components and minimal JS for HTMX interactions.
 */

/* ── Alpine.js Store: Theme ─────────────────────────────────────────── */
document.addEventListener('alpine:init', () => {
  Alpine.store('theme', {
    current: localStorage.getItem('theme') || 'obsidian',

    init() {
      // Set initial theme on page load
      document.documentElement.setAttribute('data-theme', this.current);
    },

    toggle() {
      this.current = this.current === 'obsidian' ? 'light' : 'obsidian';
      localStorage.setItem('theme', this.current);
      document.documentElement.setAttribute('data-theme', this.current);
    },
  });

  // Incident Response Chat
  Alpine.data('incidentResponse', () => ({
    phase: 'input',  // input | diagnosing | diagnosis | investigating | resolved
    alertText: '',
    severity: 'P2',
    sessionId: '',
    messages: [],
    loading: false,

    async submitAlert() {
      if (!this.alertText.trim()) return;
      this.phase = 'diagnosing';
      this.loading = true;
      this.messages.push({
        type: 'user',
        text: this.alertText,
        timestamp: new Date().toLocaleTimeString(),
      });

      try {
        const formData = new FormData();
        formData.append('alert_text', this.alertText);
        formData.append('severity', this.severity);

        const response = await fetch('/api/incidents/respond', {
          method: 'POST',
          body: formData,
        });
        const html = await response.text();
        this.messages.push({
          type: 'agent',
          html: html,
          timestamp: new Date().toLocaleTimeString(),
        });
        this.phase = 'diagnosis';
      } catch (err) {
        this.messages.push({
          type: 'error',
          text: 'Failed to get diagnosis. Please try again.',
          timestamp: new Date().toLocaleTimeString(),
        });
        this.phase = 'input';
      }
      this.loading = false;
    },

    async continueInvestigation(newInfo) {
      if (!newInfo.trim()) return;
      this.phase = 'diagnosing';
      this.loading = true;
      this.messages.push({
        type: 'user',
        text: newInfo,
        timestamp: new Date().toLocaleTimeString(),
      });

      try {
        const formData = new FormData();
        formData.append('new_info', newInfo);
        formData.append('session_id', this.sessionId);

        const response = await fetch('/api/incidents/continue', {
          method: 'POST',
          body: formData,
        });
        const html = await response.text();
        this.messages.push({
          type: 'agent',
          html: html,
          timestamp: new Date().toLocaleTimeString(),
        });
        this.phase = 'diagnosis';
      } catch (err) {
        this.messages.push({
          type: 'error',
          text: 'Failed to update investigation.',
          timestamp: new Date().toLocaleTimeString(),
        });
        this.phase = 'diagnosis';
      }
      this.loading = false;
    },

    async resolveIncident(resolution) {
      if (!resolution.trim()) return;
      this.loading = true;
      this.messages.push({
        type: 'user',
        text: `Resolution: ${resolution}`,
        timestamp: new Date().toLocaleTimeString(),
      });

      try {
        const formData = new FormData();
        formData.append('resolution', resolution);
        formData.append('session_id', this.sessionId);

        const response = await fetch('/api/incidents/resolve', {
          method: 'POST',
          body: formData,
        });
        const html = await response.text();
        this.messages.push({
          type: 'agent',
          html: html,
          timestamp: new Date().toLocaleTimeString(),
        });
        this.phase = 'resolved';
      } catch (err) {
        this.messages.push({
          type: 'error',
          text: 'Failed to resolve incident.',
          timestamp: new Date().toLocaleTimeString(),
        });
      }
      this.loading = false;
    },
  }));

  // Demo Mode
  Alpine.data('demoMode', () => ({
    currentAct: 1,
    autoPlay: false,
    autoPlayInterval: null,
    totalActs: 5,

    get acts() {
      return [
        { number: 1, title: 'Build the Brain', icon: '🧠' },
        { number: 2, title: 'The Morning After', icon: '🚨' },
        { number: 3, title: 'Self-Improvement', icon: '✨' },
        { number: 4, title: 'Knowledge Gaps', icon: '🔍' },
        { number: 5, title: 'The Pitch', icon: '🚀' },
      ];
    },

    goToAct(actNumber) {
      this.currentAct = actNumber;
    },

    nextAct() {
      if (this.currentAct < this.totalActs) {
        this.currentAct++;
      } else {
        this.stopAutoPlay();
      }
    },

    prevAct() {
      if (this.currentAct > 1) {
        this.currentAct--;
      }
    },

    toggleAutoPlay() {
      this.autoPlay = !this.autoPlay;
      if (this.autoPlay) {
        this.autoPlayInterval = setInterval(() => {
          this.nextAct();
        }, 8000);
      } else {
        this.stopAutoPlay();
      }
    },

    stopAutoPlay() {
      this.autoPlay = false;
      if (this.autoPlayInterval) {
        clearInterval(this.autoPlayInterval);
        this.autoPlayInterval = null;
      }
    },
  }));

  // Sidebar Toggle
  Alpine.data('sidebar', () => ({
    open: false,
    toggle() {
      this.open = !this.open;
    },
  }));

  // Postmortem Accordion
  Alpine.data('accordion', () => ({
    openItems: new Set(),
    toggle(id) {
      if (this.openItems.has(id)) {
        this.openItems.delete(id);
      } else {
        this.openItems.add(id);
      }
    },
    isOpen(id) {
      return this.openItems.has(id);
    },
  }));
});

/* ── HTMX Event Listeners ───────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  // Add loading class to body during HTMX requests
  document.body.addEventListener('htmx:request', () => {
    document.body.classList.add('htmx-requesting');
  });

  document.body.addEventListener('htmx:afterSwap', () => {
    document.body.classList.remove('htmx-requesting');
  });

  // Animate elements on HTMX swap
  document.body.addEventListener('htmx:afterSwap', (event) => {
    const target = event.detail.target;
    if (target) {
      target.classList.add('animate-fade-in');
      setTimeout(() => target.classList.remove('animate-fade-in'), 500);
    }
  });
});
