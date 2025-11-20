const { createApp } = Vue;

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

createApp({
  data() {
    return {
      user: null,
      loading: true,
      loginForm: { username: '', password: '' },
      newRequest: { start_date: '', end_date: '' },
      error: '',
      balance: 0,
      myRequests: [],
      managerRequests: [],
      hrRequests: [],
      notifications: [],
      unreadCount: 0,
    };
  },
  methods: {
    csrfHeader() {
      return { 'X-CSRFToken': getCookie('csrftoken') || '' };
    },
    async fetchJson(url, options = {}) {
      const opts = Object.assign({
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...this.csrfHeader() },
      }, options);
      const response = await fetch(url, opts);
      const contentType = response.headers.get('content-type') || '';
      let data = null;
      if (contentType.includes('application/json')) {
        data = await response.json();
      }
      if (!response.ok) {
        const message = data && data.error ? data.error : 'Ошибка запроса';
        throw new Error(message);
      }
      return data;
    },
    async loadMe() {
      this.loading = true;
      try {
        const data = await this.fetchJson('/api/me');
        if (data.authenticated) {
          this.user = data.user;
          await this.postLoginLoad();
        } else {
          this.user = null;
        }
      } catch (err) {
        console.error(err);
      } finally {
        this.loading = false;
      }
    },
    async postLoginLoad() {
      this.error = '';
      await Promise.all([
        this.refreshNotifications(),
        this.loadRoleData(),
      ]);
    },
    async loadRoleData() {
      if (!this.user) return;
      if (this.user.role === 'employee') {
        await Promise.all([this.loadBalance(), this.loadMyRequests()]);
      } else if (this.user.role === 'manager') {
        await this.loadManagerRequests();
      } else if (this.user.role === 'hr') {
        await this.loadHrRequests();
      }
    },
    async login() {
      this.error = '';
      try {
        await this.fetchJson('/api/login', {
          method: 'POST',
          body: JSON.stringify(this.loginForm),
        });
        await this.loadMe();
      } catch (err) {
        this.error = err.message;
      }
    },
    async logout() {
      try {
        await this.fetchJson('/api/logout', { method: 'POST' });
      } catch (err) {
        console.error(err);
      }
      this.user = null;
      this.myRequests = [];
      this.managerRequests = [];
      this.hrRequests = [];
      this.notifications = [];
      this.unreadCount = 0;
    },
    async loadBalance() {
      try {
        const data = await this.fetchJson('/api/vacation/balance');
        this.balance = data.days_remaining;
      } catch (err) {
        console.error(err);
      }
    },
    async loadMyRequests() {
      try {
        const data = await this.fetchJson('/api/vacation/requests/my');
        this.myRequests = data.requests;
      } catch (err) {
        console.error(err);
      }
    },
    async createRequest() {
      try {
        await this.fetchJson('/api/vacation/request', {
          method: 'POST',
          body: JSON.stringify(this.newRequest),
        });
        this.newRequest = { start_date: '', end_date: '' };
        await this.loadMyRequests();
      } catch (err) {
        alert(err.message);
      }
    },
    async confirmRequest(id) {
      try {
        await this.fetchJson(`/api/vacation/request/${id}/confirm`, { method: 'POST' });
        await this.loadMyRequests();
      } catch (err) {
        alert(err.message);
      }
    },
    async loadManagerRequests() {
      try {
        const data = await this.fetchJson('/api/manager/requests');
        this.managerRequests = data.requests;
      } catch (err) {
        console.error(err);
      }
    },
    async approveRequest(id) {
      try {
        await this.fetchJson(`/api/manager/request/${id}/approve`, { method: 'POST' });
        await this.loadManagerRequests();
      } catch (err) {
        alert(err.message);
      }
    },
    async rejectRequest(id) {
      try {
        await this.fetchJson(`/api/manager/request/${id}/reject`, { method: 'POST' });
        await this.loadManagerRequests();
      } catch (err) {
        alert(err.message);
      }
    },
    async loadHrRequests() {
      try {
        const data = await this.fetchJson('/api/hr/requests');
        this.hrRequests = data.requests;
      } catch (err) {
        console.error(err);
      }
    },
    async exportCsv() {
      try {
        const response = await fetch('/api/hr/export', {
          credentials: 'include',
          headers: this.csrfHeader(),
        });
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'vacation_approved.csv';
        a.click();
        window.URL.revokeObjectURL(url);
      } catch (err) {
        alert('Не удалось скачать файл');
      }
    },
    async loadNotifications() {
      if (!this.user) return;
      try {
        const data = await this.fetchJson('/api/notifications');
        this.notifications = data.notifications;
      } catch (err) {
        console.error(err);
      }
    },
    async refreshNotifications() {
      if (!this.user) return;
      try {
        const data = await this.fetchJson('/api/notifications/unread_count');
        this.unreadCount = data.unread_count;
      } catch (err) {
        console.error(err);
      }
    },
    async markNotificationRead(id) {
      try {
        await this.fetchJson(`/api/notifications/${id}/read`, { method: 'POST' });
        await Promise.all([this.loadNotifications(), this.refreshNotifications()]);
      } catch (err) {
        console.error(err);
      }
    },
  },
  async mounted() {
    await this.loadMe();
    await this.loadNotifications();
  },
}).mount('#app');
