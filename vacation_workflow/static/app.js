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
      editingRequestId: null,
      editRequestForm: { start_date: '', end_date: '' },
      // --- ДЛЯ ГРАФИКА ---
      hrSchedule: [],
      hrScheduleYear: new Date().getFullYear(),
      hrSelectedManagerId: '',
      hrDepartments: [],
      loadingHrSchedule: false,
      hrCalendarMonths: ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'],
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
      setTimeout(() => {
        if (toast.parentNode === container) {
          container.removeChild(toast);
        }
      }, 2600);
    },
    startBalanceAutoRefresh() {
      this.stopBalanceAutoRefresh();
      if (!this.user || this.user.role !== 'employee') {
        return;
      }
      this.balanceAutoRefreshId = setInterval(() => {
        if (this.user && this.user.role === 'employee') {
          this.loadBalance(true);
          this.fetchVacationBalances();
        }
      }, 2000);
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
      if (this.user && this.user.role === 'employee') {
        this.startBalanceAutoRefresh();
      }
    },
    async loadRoleData() {
      if (!this.user) return;
      if (this.user.role === 'employee') {
        this.loadingEmployeeData = true;
        await new Promise(resolve => setTimeout(resolve, 1000));
        await Promise.all([
          this.loadBalance(),
          this.loadMyRequests(),
          this.fetchVacationBalances(),
        ]);
        this.loadingEmployeeData = false;
      } else if (this.user.role === 'manager') {
        this.loadingManagerData = true;
        await new Promise(resolve => setTimeout(resolve, 1000));
        await Promise.all([
          this.loadManagerRequests(),
          this.fetchVacationBalances(),
        ]);
        this.loadingManagerData = false;
      } else if (this.user.role === 'hr') {
        this.loadingHrData = true;
        await new Promise(resolve => setTimeout(resolve, 1000));
        await Promise.all([
          this.loadHrRequests(),
          this.fetchVacationBalances(),
          this.loadHrSchedule(),
          this.loadHrDepartments(),
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
      } catch (err) {
        console.error(err);
      } finally {
        this.loadingEmployeeData = false;
      }
    },
    startEditRequest(request) {
      if (!request) return;
      // Разрешаем редактировать только заявки в статусе "pending" (на согласовании)
      if (request.status !== 'pending') {
        this.showToast('Изменять можно только заявки, которые ещё на согласовании', 'error');
        return;
      }
      this.editingRequestId = request.id;
      this.editRequestForm = {
        start_date: request.start_date,
        end_date: request.end_date,
      };
      this.showToast('Измените даты и нажмите «Сохранить».', 'info');
    },
    async saveEditedRequest(id) {
      if (!id) return;
      const { start_date, end_date } = this.editRequestForm || {};
      if (!start_date || !end_date) {
        this.showToast('Выберите даты начала и окончания отпуска', 'error');
        return;
      }
      if (end_date < start_date) {
        this.showToast('Дата окончания не может быть раньше даты начала', 'error');
        return;
      }
      try {
        await this.fetchJson(`/api/vacation/request/${id}/update`, {
          method: 'POST',
          body: JSON.stringify({ start_date, end_date }),
        });
        this.editingRequestId = null;
        this.editRequestForm = { start_date: '', end_date: '' };
        await Promise.all([
          this.loadMyRequests(),
          this.fetchVacationBalances(),
        ]);
        this.showToast('Период заявки обновлён', 'success');
      } catch (err) {
        this.showToast(err.message || 'Не удалось обновить заявку', 'error');
      }
    },
    cancelEditRequest() {
      this.editingRequestId = null;
      this.editRequestForm = { start_date: '', end_date: '' };
    },
    async createRequest() {
      // Общая валидация диапазона дат
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

        // Сбрасываем форму и состояние редактирования
        this.newRequest = { start_date: '', end_date: '' };
        this.dateRangeInfo = { days: 0, valid: false };
        this.dateRangeError = '';
        this.editingRequestId = null;

        // Обновляем список заявок (и, на всякий случай, остатки)
        await Promise.all([
          this.loadMyRequests(),
          this.fetchVacationBalances(),
        ]);

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
      const days = Math.round(diffMs / oneDayMs) + 1;

      this.dateRangeInfo = { days, valid: true };

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
        await new Promise(resolve => setTimeout(resolve, 1000));
        const data = await this.fetchJson('/api/notifications');
        const raw = data.notifications || [];
        this.notifications = raw.map(n => ({
          ...n,
          display_text: this.formatNotificationText(n),
        }));
      } catch (err) {
        console.error(err);
      } finally {
        this.loadingNotifications = false;
      }
    },
    formatNotificationText(notification) {
      if (!notification) return '';
      if (notification.message) {
        return notification.message;
      }
      const created = notification.created_at || '';
      const type = notification.type || '';
      if (type === 'vacation_reminder_14d') {
        return `Через 14 дней начинается отпуск по одной из ваших заявок (создано: ${created})`;
      }
      if (type === 'vacation_start_today') {
        return `Сегодня начинается отпуск по одной из ваших заявок (создано: ${created})`;
      }
      return `Уведомление (${created})`;
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
    setHrScheduleYear(year) {
      this.hrScheduleYear = year;
      this.loadHrSchedule();
    },
    async loadHrDepartments() {
      if (!this.user || this.user.role !== 'hr') return;
      try {
        const data = await this.fetchJson('/api/hr/departments');
        this.hrDepartments = data.departments || [];
      } catch (err) {
        console.error('Failed to load departments', err);
      }
    },
    async loadHrSchedule() {
      if (!this.user || this.user.role !== 'hr') return;
      this.loadingHrSchedule = true;
      try {
        let url = `/api/hr/schedule?year=${this.hrScheduleYear}`;
        if (this.hrSelectedManagerId) {
          url += `&manager_id=${encodeURIComponent(this.hrSelectedManagerId)}`;
        }
        const data = await this.fetchJson(url);
        this.hrSchedule = data.entries || [];
      } catch (err) {
        console.error('Failed to load HR schedule', err);
      } finally {
        this.loadingHrSchedule = false;
      }
    },
    async exportHrScheduleCsv() {
      if (!this.user || this.user.role !== 'hr') return;
      try {
        let url = `/api/hr/schedule/export?year=${this.hrScheduleYear}`;
        if (this.hrSelectedManagerId) {
          url += `&manager_id=${encodeURIComponent(this.hrSelectedManagerId)}`;
        }
        const response = await fetch(url, {
          credentials: 'include',
          headers: this.csrfHeader(),
        });
        if (!response.ok) {
          throw new Error('Не удалось скачать график');
        }
        const blob = await response.blob();
        const dlUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = dlUrl;
        const suffix = this.hrSelectedManagerId ? `_manager_${this.hrSelectedManagerId}` : '';
        a.download = `vacation_schedule_${this.hrScheduleYear}${suffix}.csv`;
        a.click();
        window.URL.revokeObjectURL(dlUrl);
        this.showToast('CSV-файл графика скачан', 'success');
      } catch (err) {
        this.showToast(err.message || 'Не удалось скачать график', 'error');
      }
    },
    openHrPrintView() {
      if (!this.user || this.user.role !== 'hr') return;
      let url = `/api/hr/schedule/print?year=${this.hrScheduleYear}`;
      if (this.hrSelectedManagerId) {
        url += `&manager_id=${encodeURIComponent(this.hrSelectedManagerId)}`;
      }
      window.open(url, '_blank');
    },
    getDaysBetween(start, end) {
      if (!start || !end) return '';
      const startDate = new Date(start);
      const endDate = new Date(end);
      if (isNaN(startDate) || isNaN(endDate)) return '';
      const diffMs = endDate.getTime() - startDate.getTime();
      const days = Math.floor(diffMs / (1000 * 60 * 60 * 24)) + 1;
      return days;
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
  computed: {
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
    hrCalendarRows() {
      // Готовим строки для календарной сетки по месяцам
      const year = this.hrScheduleYear;
      return (this.hrSchedule || []).map(entry => {
        const months = [];
        for (let m = 0; m < 12; m++) {
          let hasVacation = false;
          const periods = [];
          (entry.periods || []).forEach(p => {
            const start = new Date(p.start_date);
            const end = new Date(p.end_date);
            if (isNaN(start) || isNaN(end)) return;
            if (start.getFullYear() > year || end.getFullYear() < year) return;
            const mStart = start.getMonth();
            const mEnd = end.getMonth();
            if (m >= mStart && m <= mEnd) {
              hasVacation = true;
              periods.push(p);
            }
          });
          months.push({
            monthIndex: m,
            hasVacation,
            periods,
          });
        }
        return {
          ...entry,
          months,
        };
      });
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
