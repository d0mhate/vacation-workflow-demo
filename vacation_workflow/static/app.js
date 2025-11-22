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
      dateRangeInfo: { days: 0, valid: false },
      dateRangeError: '',
      error: '',
      balance: 0,
      balances: [],
      myRequests: [],
      sortMyField: 'id',
      sortMyDirection: 'asc',
      managerRequests: [],
      sortManagerField: 'id',
      sortManagerDirection: 'asc',
      hrRequests: [],
      sortHrField: 'id',
      sortHrDirection: 'asc',
      notifications: [],
      unreadCount: 0,
      loadingNotifications: false,
      loadingEmployeeData: false,
      loadingManagerData: false,
      loadingHrData: false,
      toastTimeoutId: null,
      showProfileModal: false,
      balanceAutoRefreshId: null,
      profileForm: { first_name: '', last_name: '' },
    };
  },
  methods: {
    openProfileModal() {
      if (!this.user) return;
      this.profileForm.first_name = this.user.first_name || '';
      this.profileForm.last_name = this.user.last_name || '';
      this.showProfileModal = true;
    },
    async saveProfile() {
      try {
        const payload = {
          first_name: this.profileForm.first_name,
          last_name: this.profileForm.last_name
        };
        const data = await this.fetchJson('/api/profile/update', {
          method: 'POST',
          body: JSON.stringify(payload)
        });
        if (data && data.user) {
          this.user.first_name = data.user.first_name;
          this.user.last_name = data.user.last_name;
        }
        this.showProfileModal = false;
        this.showToast('Профиль обновлен', 'success');
      } catch (err) {
        console.error(err);
        this.showToast('Не удалось сохранить профиль', 'error');
      }
    },
    csrfHeader() {
      return { 'X-CSRFToken': getCookie('csrftoken') || '' };
    },
    showToast(message, type = 'info') {
      const container = document.getElementById('toast');
      if (!container) return;
      const toast = document.createElement('div');
      toast.className = 'toast';
      if (type === 'error') {
        toast.classList.add('toast-error');
      } else if (type === 'success') {
        toast.classList.add('toast-success');
      }
      toast.textContent = message;
      container.appendChild(toast);
      // автоматически удалить тост после завершения анимации
      setTimeout(() => {
        if (toast.parentNode === container) {
          container.removeChild(toast);
        }
      }, 2600);
    },

    startBalanceAutoRefresh() {
      // автообновление только для сотрудника, чтобы сводка отпусков была актуальной
      this.stopBalanceAutoRefresh();
      if (!this.user || this.user.role !== 'employee') {
        return;
      }
      this.balanceAutoRefreshId = setInterval(() => {
        // если пользователь все еще сотрудник на этой странице — обновляем остаток и сводку
        if (this.user && this.user.role === 'employee') {
          this.loadBalance(true); // тихое обновление без перерисовки всего блока
          this.fetchVacationBalances();
        }
      }, 2000); // каждые 2 секунды
    },

    stopBalanceAutoRefresh() {
      if (this.balanceAutoRefreshId) {
        clearInterval(this.balanceAutoRefreshId);
        this.balanceAutoRefreshId = null;
      }
    },
    scrollToNotifications() {
      const el = document.getElementById('notifications-card');
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
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
          // запускаем загрузку данных после логина асинхронно,
          // чтобы основной UI отрисовался, а уведомления могли
          // показывать скелетон
          this.postLoginLoad();
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
        this.loadNotifications(),
      ]);
    },
    async loadRoleData() {
      if (!this.user) return;
      if (this.user.role === 'employee') {
        this.loadingEmployeeData = true;
        // artificial delay to simulate slow backend for "Мои данные"
        await new Promise(resolve => setTimeout(resolve, 1000));
        await Promise.all([
          this.loadBalance(),
          this.loadMyRequests(),
          this.fetchVacationBalances(),
        ]);
        this.loadingEmployeeData = false;
      } else if (this.user.role === 'manager') {
        this.loadingManagerData = true;
        // artificial delay to simulate slow backend for локальное тестирование
        await new Promise(resolve => setTimeout(resolve, 1000));
        await Promise.all([
          this.loadManagerRequests(),
          this.fetchVacationBalances(),
        ]);
        this.loadingManagerData = false;
      } else if (this.user.role === 'hr') {
        this.loadingHrData = true;
        // artificial delay to simulate slow backend for локальное тестирование
        await new Promise(resolve => setTimeout(resolve, 1000));
        await Promise.all([
          this.loadHrRequests(),
          this.fetchVacationBalances(),
        ]);
        this.loadingHrData = false;
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
        this.startBalanceAutoRefresh();
      } catch (err) {
        this.error = err.message;
      }
    },
    async logout() {
      this.stopBalanceAutoRefresh();
      try {
        await this.fetchJson('/api/logout', { method: 'POST' });
      } catch (err) {
        console.error(err);
      }
      this.user = null;
      this.showProfileModal = false;
      this.myRequests = [];
      this.managerRequests = [];
      this.hrRequests = [];
      this.balances = [];
      this.notifications = [];
      this.unreadCount = 0;
    },
    async loadBalance(silent = false) {
      if (!silent) {
        this.loadingEmployeeData = true;
      }
      try {
        const data = await this.fetchJson('/api/vacation/balance');
        this.balance = data.days_remaining;
      } catch (err) {
        console.error(err);
      } finally {
        if (!silent) {
          this.loadingEmployeeData = false;
        }
      }
    },
    async loadMyRequests() {
      this.loadingEmployeeData = true;
      try {
        const data = await this.fetchJson('/api/vacation/requests/my');
        this.myRequests = data.requests;
        this.loadingEmployeeData = false;
      } catch (err) {
        console.error(err);
        this.loadingEmployeeData = false;
      }
    },
    async createRequest() {
      // пересчитываем данные по диапазону дат
      this.updateDateRangeInfo();

      if (!this.newRequest.start_date || !this.newRequest.end_date) {
        this.showToast('Выберите даты начала и окончания отпуска', 'error');
        return;
      }

      if (!this.dateRangeInfo.valid) {
        this.showToast(this.dateRangeError || 'Некорректный диапазон дат', 'error');
        return;
      }

      try {
        await this.fetchJson('/api/vacation/request', {
          method: 'POST',
          body: JSON.stringify(this.newRequest),
        });
        this.newRequest = { start_date: '', end_date: '' };
        this.dateRangeInfo = { days: 0, valid: false };
        this.dateRangeError = '';
        await this.loadMyRequests();
        this.showToast('Заявка отправлена на согласование', 'success');
      } catch (err) {
        this.showToast(err.message, 'error');
      }
    },
    updateDateRangeInfo() {
      const { start_date, end_date } = this.newRequest;
      this.dateRangeError = '';

      if (!start_date || !end_date) {
        this.dateRangeInfo = { days: 0, valid: false };
        return;
      }

      if (end_date < start_date) {
        this.dateRangeInfo = { days: 0, valid: false };
        this.dateRangeError = 'Дата окончания не может быть раньше даты начала';
        return;
      }

      const start = new Date(start_date);
      const end = new Date(end_date);
      const diffMs = end.getTime() - start.getTime();
      const oneDayMs = 24 * 60 * 60 * 1000;
      const days = Math.round(diffMs / oneDayMs) + 1; // включая оба дня

      // базовая проверка диапазона
      this.dateRangeInfo = { days, valid: true };

      // проверка: нельзя выбрать больше, чем доступный остаток отпусков
      const available = this.balance || 0;
      if (available > 0 && days > available) {
        this.dateRangeInfo.valid = false;
        this.dateRangeError = `Вы выбрали ${days} дн., но доступно только ${available} дн.`;
      } else if (available === 0 && days > 0) {
        this.dateRangeInfo.valid = false;
        this.dateRangeError = 'У вас нет доступных дней отпуска для выбранного периода';
      }
    },
    async confirmRequest(id) {
      try {
        await this.fetchJson(`/api/vacation/request/${id}/confirm`, { method: 'POST' });
        // обновляем список заявок и остаток дней отпуска, а также сводку по остаткам
        await Promise.all([
          this.loadMyRequests(),
          this.loadBalance(true),
          this.fetchVacationBalances(),
        ]);
        this.showToast('Ознакомление с приказом подтверждено', 'success');
      } catch (err) {
        this.showToast(err.message, 'error');
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
        await Promise.all([
          this.loadManagerRequests(),
          this.fetchVacationBalances(),
        ]);
        this.showToast('Заявка согласована', 'success');
      } catch (err) {
        this.showToast(err.message, 'error');
      }
    },
    async rejectRequest(id) {
      try {
        await this.fetchJson(`/api/manager/request/${id}/reject`, { method: 'POST' });
        await Promise.all([
          this.loadManagerRequests(),
          this.fetchVacationBalances(),
        ]);
        this.showToast('Заявка отклонена', 'success');
      } catch (err) {
        this.showToast(err.message, 'error');
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
        if (!response.ok) {
          throw new Error('Не удалось скачать файл');
        }
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'vacation_approved.csv';
        a.click();
        window.URL.revokeObjectURL(url);
        this.showToast('CSV-файл со сводным графиком скачан', 'success');
      } catch (err) {
        this.showToast(err.message || 'Не удалось скачать файл', 'error');
      }
    },
    async loadNotifications() {
      if (!this.user) return;
      this.loadingNotifications = true;
      try {
        // artificial delay to simulate slow backend for local testing
        await new Promise(resolve => setTimeout(resolve, 1000));
        const data = await this.fetchJson('/api/notifications');
        this.notifications = data.notifications;
        this.loadingNotifications = false;
      } catch (err) {
        console.error(err);
        this.loadingNotifications = false;
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
        this.showToast('Не удалось отметить уведомление прочитанным', 'error');
      }
    },
    async fetchVacationBalances() {
      try {
        const data = await this.fetchJson('/api/vacation/balances');
        this.balances = data.balances || [];
      } catch (err) {
        console.error('Failed to load balances', err);
      }
    },

  sortedMyRequests() {
    const list = [...this.myRequests];
    if (!this.sortMyField) {
      return list;
    }
    const dir = this.sortMyDirection === 'asc' ? 1 : -1;
    list.sort((a, b) => {
      if (this.sortMyField === 'id') {
        return dir * (a.id - b.id);
      }
      if (this.sortMyField === 'period') {
        const aDate = a.start_date || '';
        const bDate = b.start_date || '';
        return dir * aDate.localeCompare(bDate);
      }
      if (this.sortMyField === 'status') {
        const aStatus = a.status || '';
        const bStatus = b.status || '';
        return dir * aStatus.localeCompare(bStatus);
      }
      if (this.sortMyField === 'confirmed' || this.sortMyField === 'actions') {
        const aVal = a.confirmed_by_employee ? 1 : 0;
        const bVal = b.confirmed_by_employee ? 1 : 0;
        return dir * (aVal - bVal);
      }
      return 0;
    });
    return list;
  },

  sortedManagerRequests() {
    const list = [...this.managerRequests];
    if (!this.sortManagerField) {
      return list;
    }
    const dir = this.sortManagerDirection === 'asc' ? 1 : -1;
    list.sort((a, b) => {
      if (this.sortManagerField === 'id') {
        return dir * (a.id - b.id);
      }
      if (this.sortManagerField === 'period') {
        const aDate = a.start_date || '';
        const bDate = b.start_date || '';
        return dir * aDate.localeCompare(bDate);
      }
      if (this.sortManagerField === 'status') {
        const aStatus = a.status || '';
        const bStatus = b.status || '';
        return dir * aStatus.localeCompare(bStatus);
      }
      if (this.sortManagerField === 'confirmed') {
        const aVal = a.confirmed_by_employee ? 1 : 0;
        const bVal = b.confirmed_by_employee ? 1 : 0;
        return dir * (aVal - bVal);
      }
      return 0;
    });
    return list;
  },

  sortedHrRequests() {
    const list = [...this.hrRequests];
    if (!this.sortHrField) {
      return list;
    }
    const dir = this.sortHrDirection === 'asc' ? 1 : -1;
    list.sort((a, b) => {
      if (this.sortHrField === 'id') {
        return dir * (a.id - b.id);
      }
      if (this.sortHrField === 'period') {
        const aDate = a.start_date || '';
        const bDate = b.start_date || '';
        return dir * aDate.localeCompare(bDate);
      }
      if (this.sortHrField === 'status') {
        const aStatus = a.status || '';
        const bStatus = b.status || '';
        return dir * aStatus.localeCompare(bStatus);
      }
      if (this.sortHrField === 'confirmed') {
        const aVal = a.confirmed_by_employee ? 1 : 0;
        const bVal = b.confirmed_by_employee ? 1 : 0;
        return dir * (aVal - bVal);
      }
      return 0;
    });
    return list;
  },

    toggleMySort(field) {
      if (this.sortMyField === field) {
        this.sortMyDirection = this.sortMyDirection === 'asc' ? 'desc' : 'asc';
      } else {
        this.sortMyField = field;
        this.sortMyDirection = 'asc';
      }
    },

    toggleManagerSort(field) {
      if (this.sortManagerField === field) {
        this.sortManagerDirection = this.sortManagerDirection === 'asc' ? 'desc' : 'asc';
      } else {
        this.sortManagerField = field;
        this.sortManagerDirection = 'asc';
      }
    },

    toggleHrSort(field) {
      if (this.sortHrField === field) {
        this.sortHrDirection = this.sortHrDirection === 'asc' ? 'desc' : 'asc';
      } else {
        this.sortHrField = field;
        this.sortHrDirection = 'asc';
      }
    },
  },
  watch: {
    'newRequest.start_date'() {
      this.updateDateRangeInfo();
    },
    'newRequest.end_date'() {
      this.updateDateRangeInfo();
    },
  },
  async mounted() {
    await this.loadMe();
    if (this.user && this.user.role === 'employee') {
      this.startBalanceAutoRefresh();
    }
  },
}).mount('#app');
