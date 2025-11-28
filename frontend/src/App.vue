<template>
  <div>
    <header>
      <div><strong>Vacation Workflow</strong></div>
      <div v-if="user">
        <span>{{ user.first_name }} {{ user.last_name }} ({{ user.username }}, {{ user.role }})</span>
        <span class="badge" title="Unread notifications">{{ unreadCount }}</span>
        <button @click="openProfileModal" class="secondary" style="margin-right: 8px;">
          Профиль
        </button>
        <button @click="logout">Выйти</button>
      </div>
    </header>

    <div v-if="loading">Загрузка...</div>

    <div v-else>
      <div id="toast" class="toast-container"></div>
      <div v-if="!user" class="card login-card">
        <div class="muted login-subtitle">
          Введите логин и пароль, выданные кадровой службой.
        </div>
        <form @submit.prevent="login" class="auth-form">
          <div class="form-group">
            <label for="login-username">Логин</label>
            <input
              id="login-username"
              type="text"
              v-model="loginForm.username"
              required
            >
          </div>
          <div class="form-group">
            <label for="login-password">Пароль</label>
            <input
              id="login-password"
              type="password"
              v-model="loginForm.password"
              required
            >
          </div>
          <div class="form-actions">
            <button type="submit">Войти</button>
          </div>
        </form>
        <div class="error-text" v-if="error">{{ error }}</div>
      </div>

      <div v-else>
        <section v-if="user.role === 'employee'" class="card">
          <div class="muted">Личный кабинет сотрудника. Здесь вы можете видеть остаток отпуска и управлять своими заявками.</div>
          <br>
          <transition name="fade">
            <div v-if="loadingEmployeeData" class="loading-skeleton" style="margin-top: 8px;">
              <div class="skeleton-line"></div>
              <div class="skeleton-line"></div>
              <div class="skeleton-line short"></div>
            </div>

            <div v-else>
              <div>Остаток отпуска: {{ balance }} дней</div>

              <div v-if="balances && balances.length" class="balances-block">
                <h4>Остаток отпусков</h4>
                <table class="simple-table">
                  <thead>
                    <tr>
                      <th>Год</th>
                      <th>Остаток, дней</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="b in balances" :key="b.id">
                      <td>{{ b.year }}</td>
                      <td>{{ b.days_remaining }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <h4>Мои заявки</h4>
              <div v-if="myRequests.length">
                <div style="display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:6px 0 4px;">
                  <span class="muted" style="font-size:13px;">Сортировать по:</span>
                  <button type="button" class="secondary" @click="toggleMySort('id')">
                    ID
                    <span v-if="sortMyField === 'id'">
                      <span v-if="sortMyDirection === 'asc'">↑</span>
                      <span v-else>↓</span>
                    </span>
                  </button>
                  <button type="button" class="secondary" @click="toggleMySort('period')">
                    Период
                    <span v-if="sortMyField === 'period'">
                      <span v-if="sortMyDirection === 'asc'">↑</span>
                      <span v-else>↓</span>
                    </span>
                  </button>
                  <button type="button" class="secondary" @click="toggleMySort('status')">
                    Статус
                    <span v-if="sortMyField === 'status'">
                      <span v-if="sortMyDirection === 'asc'">↑</span>
                      <span v-else>↓</span>
                    </span>
                  </button>
                  <button type="button" class="secondary" @click="toggleMySort('confirmed')">
                    Подтверждено
                    <span v-if="sortMyField === 'confirmed'">
                      <span v-if="sortMyDirection === 'asc'">↑</span>
                      <span v-else>↓</span>
                    </span>
                  </button>
                </div>
                <div class="requests-grid">
                  <div
                    v-for="req in sortedMyRequests"
                    :key="req.id"
                    class="request-card"
                    :class="{ 'request-card--not-approved': req.status !== 'approved' }"
                  >
                    <div class="request-card-header">
                      Заявка №{{ req.id }}
                    </div>
                    <div class="request-card-period">
                      Период: {{ req.start_date }} - {{ req.end_date }} ({{ getDaysBetween(req.start_date, req.end_date) }} .дн)
                    </div>
                    <div>
                      Статус:
                      <span
                        class="status-pill"
                        :class="{
                          'status-approved': req.status === 'approved',
                          'status-rejected': req.status === 'rejected',
                          'status-pending': req.status === 'pending'
                        }"
                      >
                        {{ req.status === 'approved'
                          ? 'Согласована'
                          : req.status === 'rejected'
                            ? 'Отклонена'
                            : 'На согласовании' }}
                      </span>
                    </div>
                    <div>
                      Подтверждение:
                      <span
                        :class="req.confirmed_by_employee ? 'request-confirmed-tag' : 'request-not-confirmed-tag'"
                      >
                        {{ req.confirmed_by_employee ? 'Ознакомлен' : 'Не ознакомлен' }}
                      </span>
                    </div>
                    <div class="request-card-footer">
                      <button
                        v-if="!req.confirmed_by_employee"
                        @click="confirmRequest(req.id)"
                      >
                        Подтвердить ознакомление
                      </button>
                      <button
                        v-if="canModifyRequest(req)"
                        type="button"
                        class="secondary"
                        @click="startEditRequest(req)"
                      >
                        Изменить период
                      </button>
                      <button
                        type="button"
                        class="secondary"
                        @click="duplicateRequest(req.id)"
                      >
                        Дублировать
                      </button>
                      <button
                        v-if="canDeleteRequest(req)"
                        type="button"
                        class="secondary danger icon-button"
                        @click="deleteRequest(req.id)"
                        aria-label="Удалить заявку"
                        title="Удалить заявку"
                      >
                        <svg class="icon-trash" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M9 3h6a1 1 0 0 1 1 1v1h4v2h-1v11a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3V7H4V5h4V4a1 1 0 0 1 1-1zm1 2h4V5h-4zM8 7v11a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V7z" fill="currentColor"/>
                        </svg>
                      </button>
                    </div>
                    <div v-if="editingRequestId === req.id" class="edit-request-inline">
                      <div class="muted" style="font-size:13px; margin-top:4px; margin-bottom:4px;">
                        Редактирование периода:
                      </div>

                      <div class="range-form-row" style="margin-bottom:6px;">
                        <label>
                          Начало:
                          <input
                            type="date"
                            v-model="editRequestForm.start_date"
                            required
                          >
                        </label>
                        <label>
                          Конец:
                          <input
                            type="date"
                            v-model="editRequestForm.end_date"
                            required
                          >
                        </label>
                      </div>

                      <div class="muted" style="font-size:12px; margin-bottom:8px;">
                        Выбранный диапазон: {{ getDaysBetween(editRequestForm.start_date, editRequestForm.end_date) }} дней
                      </div>

                      <div class="request-card-footer" style="margin-top:4px;">
                        <button type="button" @click="saveEditedRequest(req.id)">
                          Сохранить
                        </button>
                        <button type="button" class="secondary" @click="cancelEditRequest">
                          Отмена
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="muted" style="text-align:center; margin-top:6px;">
                Заявок пока нет
              </div>
              <h4>Новая заявка</h4>
              <form @submit.prevent="createRequest" class="range-form">
                <div class="range-form-row">
                  <label>
                    Начало:
                    <input
                      type="date"
                      v-model="newRequest.start_date"
                      required
                    >
                  </label>
                  <label>
                    Конец:
                    <input
                      type="date"
                      v-model="newRequest.end_date"
                      required
                    >
                  </label>
                  <button type="submit">Отправить</button>
                </div>
              </form>
            </div>
          </transition>
        </section>

        <section v-if="user.role === 'manager'" class="card">
          <h3>Заявки сотрудников</h3>
          <div class="muted">Кабинет руководителя. Вы согласовываете заявки сотрудников вашего подразделения.</div>
          <transition name="fade">
            <div v-if="loadingManagerData" class="loading-skeleton" style="margin-top: 8px;">
              <div class="skeleton-line"></div>
              <div class="skeleton-line"></div>
              <div class="skeleton-line short"></div>
            </div>
            <div v-else>
              <div v-if="managerRequests.length">
                <div style="display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:6px 0 4px;">
                  <span class="muted" style="font-size:13px;">Сортировать по:</span>
                  <button type="button" class="secondary" @click="toggleManagerSort('id')">
                    ID
                    <span v-if="sortManagerField === 'id'">
                      <span v-if="sortManagerDirection === 'asc'">↑</span>
                      <span v-else>↓</span>
                    </span>
                  </button>
                  <button type="button" class="secondary" @click="toggleManagerSort('period')">
                    Период
                    <span v-if="sortManagerField === 'period'">
                      <span v-if="sortManagerDirection === 'asc'">↑</span>
                      <span v-else>↓</span>
                    </span>
                  </button>
                  <button type="button" class="secondary" @click="toggleManagerSort('status')">
                    Статус
                    <span v-if="sortManagerField === 'status'">
                      <span v-if="sortManagerDirection === 'asc'">↑</span>
                      <span v-else>↓</span>
                    </span>
                  </button>
                  <button type="button" class="secondary" @click="toggleManagerSort('confirmed')">
                    Подтверждено
                    <span v-if="sortManagerField === 'confirmed'">
                      <span v-if="sortManagerDirection === 'asc'">↑</span>
                      <span v-else>↓</span>
                    </span>
                  </button>
                </div>
                <div class="requests-grid">
                  <div
                    v-for="req in sortedManagerRequests"
                    :key="req.id"
                    class="request-card"
                    :class="{
                      'request-card--approved': req.status === 'approved',
                      'request-card--not-approved': req.status !== 'approved'
                    }"
                  >
                    <div class="request-card-header">
                      Заявка №{{ req.id }} -  {{ req.user.first_name }} {{ req.user.last_name }}
                    </div>
                    <div class="request-card-period">
                      Период: {{ req.start_date }} - {{ req.end_date }}
                    </div>
                    <div>
                      Статус:
                      <span
                        class="status-pill"
                        :class="{
                          'status-approved': req.status === 'approved',
                          'status-rejected': req.status === 'rejected',
                          'status-pending': req.status === 'pending'
                        }"
                      >
                        {{ req.status === 'approved'
                          ? 'Согласована'
                          : req.status === 'rejected'
                            ? 'Отклонена'
                            : 'На согласовании' }}
                      </span>
                    </div>
                    <div>
                      Подтверждение сотрудником:
                      <span
                        :class="req.confirmed_by_employee ? 'request-confirmed-tag' : 'request-not-confirmed-tag'"
                      >
                        {{ req.confirmed_by_employee ? 'Ознакомлен' : 'Не ознакомлен' }}
                      </span>
                    </div>
                    <div class="request-card-footer">
                      <button @click="approveRequest(req.id)">Согласовать</button>
                      <button @click="rejectRequest(req.id)">Отклонить</button>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="muted" style="text-align:center; margin-top:6px;">
                Заявок пока нет
              </div>
            </div>
          </transition>
        </section>

        <section v-if="user.role === 'hr'" class="card">
          <h2 class="card-title">Календарный график отпусков (по месяцам)</h2>
          <p class="muted" style="margin-bottom: 8px;">
            По строкам сотрудники, по столбцам месяцы {{ hrScheduleYear }} года. Точка в ячейке означает, что в этот месяц у сотрудника есть утверждённый отпуск.
          </p>
          <div class="filters-row" style="display:flex; flex-wrap:wrap; gap:8px; align-items:flex-end; margin-bottom: 10px;">
            <label style="display:flex; flex-direction:column; font-size:13px;">
              Год
              <input type="number" v-model.number="hrScheduleYear" @change="loadHrSchedule" min="2000" max="2100" style="max-width:120px;">
            </label>
            <label style="display:flex; flex-direction:column; font-size:13px; min-width:200px;">
              Подразделение (менеджер)
              <select v-model="hrSelectedManagerId" @change="loadHrSchedule">
                <option value="">Все подразделения</option>
                <option v-for="m in hrDepartments" :key="m.id" :value="m.id">
                  {{ m.full_name || m.username }} ({{ m.username }})
                </option>
              </select>
            </label>
            <button type="button" class="secondary" @click="loadHrSchedule">Применить</button>
            <button type="button" class="secondary" @click="exportHrScheduleCsv">Экспорт графика (CSV)</button>
            <button type="button" class="secondary" @click="openHrPrintView">Печатная версия</button>
          </div>

          <div v-if="loadingHrSchedule" class="table-skeleton">
            Загрузка календарного графика...
          </div>

          <div v-else class="calendar-grid-wrapper">
            <table class="table calendar-table">
              <thead>
                <tr>
                  <th>Сотрудник</th>
                  <th v-for="month in 12" :key="month">
                    {{ ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'][month - 1] }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="hrSchedule.length === 0">
                  <td :colspan="13" class="muted">
                    На {{ hrScheduleYear }} год согласованных отпусков пока нет
                  </td>
                </tr>
                <tr v-for="row in hrSchedule" :key="'grid-' + row.user_id">
                  <td>
                    <div class="user-cell">
                      <div class="user-name">{{ row.full_name }}</div>
                      <div class="user-login muted">{{ row.username }}</div>
                    </div>
                  </td>
                  <td v-for="month in 12" :key="month">
                    <div
                      class="month-cell"
                      v-if="row.periods && row.periods.some(p => {
                        const start = new Date(p.start_date);
                        const end = new Date(p.end_date);
                        const m = month - 1;
                        const y = hrScheduleYear;
                        return (
                          (start.getFullYear() < y || (start.getFullYear() === y && start.getMonth() <= m)) &&
                          (end.getFullYear() > y || (end.getFullYear() === y && end.getMonth() >= m))
                        );
                      })"
                    >
                      •
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section v-if="user.role === 'hr'" class="card">
          <h3>Все заявки</h3>
          <div class="muted">Кабинет кадровой службы. Здесь вы работаете со сводным графиком отпусков.</div>
          <button @click="exportCsv" class="btn-primary" style="margin-top: 8px;">Экспорт в CSV</button>
          <transition name="fade">
            <div v-if="loadingHrData" class="loading-skeleton" style="margin-top: 8px;">
              <div class="skeleton-line"></div>
              <div class="skeleton-line"></div>
              <div class="skeleton-line short"></div>
            </div>
            <div v-else>
              <div v-if="hrRequests.length">
                <div style="display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:6px 0 4px;">
                  <span class="muted" style="font-size:13px;">Сортировать по:</span>
                  <button type="button" class="secondary" @click="toggleHrSort('id')">
                    ID
                    <span v-if="sortHrField === 'id'">
                      <span v-if="sortHrDirection === 'asc'">↑</span>
                      <span v-else>↓</span>
                    </span>
                  </button>
                  <button type="button" class="secondary" @click="toggleHrSort('period')">
                    Период
                    <span v-if="sortHrField === 'period'">
                      <span v-if="sortHrDirection === 'asc'">↑</span>
                      <span v-else>↓</span>
                    </span>
                  </button>
                  <button type="button" class="secondary" @click="toggleHrSort('status')">
                    Статус
                    <span v-if="sortHrField === 'status'">
                      <span v-if="sortHrDirection === 'asc'">↑</span>
                      <span v-else>↓</span>
                    </span>
                  </button>
                  <button type="button" class="secondary" @click="toggleHrSort('confirmed')">
                    Подтверждено
                    <span v-if="sortHrField === 'confirmed'">
                      <span v-if="sortHrDirection === 'asc'">↑</span>
                      <span v-else>↓</span>
                    </span>
                  </button>
                </div>
                <div class="requests-grid">
                  <div
                    v-for="req in sortedHrRequests"
                    :key="req.id"
                    class="request-card"
                    :class="{
                      'request-card--approved': req.status === 'approved',
                      'request-card--not-approved': req.status !== 'approved'
                    }"
                  >
                    <div class="request-card-header">
                      Заявка №{{ req.id }} - {{ req.user.first_name }} {{ req.user.last_name }}
                    </div>
                    <div class="request-card-period">
                      Период: {{ req.start_date }} - {{ req.end_date }}
                    </div>
                    <div>
                      Статус:
                      <span
                        class="status-pill"
                        :class="{
                          'status-approved': req.status === 'approved',
                          'status-rejected': req.status === 'rejected',
                          'status-pending': req.status === 'pending'
                        }"
                      >
                        {{ req.status === 'approved'
                          ? 'Согласована'
                          : req.status === 'rejected'
                            ? 'Отклонена'
                            : 'На согласовании' }}
                      </span>
                    </div>
                    <div>
                      Подтверждение сотрудником:
                      <span
                        :class="req.confirmed_by_employee ? 'request-confirmed-tag' : 'request-not-confirmed-tag'"
                      >
                        {{ req.confirmed_by_employee ? 'Ознакомлен' : 'Не ознакомлен' }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="muted" style="text-align:center; margin-top:6px;">
                Заявок пока нет
              </div>
            </div>
          </transition>
        </section>

        <section v-if="user.role === 'manager' || user.role === 'hr'" class="card">
          <h2 class="card-title">Таблицы отпусков на год</h2>
          <div v-if="balances && balances.length">
            <table class="simple-table">
              <thead>
                <tr>
                  <th>Сотрудник</th>
                  <th>Год</th>
                  <th>Остаток, дней</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="b in balances" :key="b.id">
                  <td>
                    {{ b.user.first_name || '' }} {{ b.user.last_name || '' }}
                    <span class="muted" v-if="!b.user.first_name && !b.user.last_name">
                      ({{ b.user.username }})
                    </span>
                  </td>
                  <td>{{ b.year }}</td>
                  <td>{{ b.days_remaining }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="muted" style="margin-top: 4px;">Нет данных по остаткам отпусков.</div>
        </section>

        <section v-if="user.role === 'hr'" class="card">
          <div class="card-header-row">
            <h2 class="card-title">График отпусков на год</h2>
            <div class="year-switcher">
              <button class="btn-secondary-small"
                      @click="setHrScheduleYear(hrScheduleYear - 1)">
                ← {{ hrScheduleYear - 1 }}
              </button>
              <span class="year-label">{{ hrScheduleYear }}</span>
              <button class="btn-secondary-small"
                      @click="setHrScheduleYear(hrScheduleYear + 1)">
                {{ hrScheduleYear + 1 }} →
              </button>
            </div>
          </div>

          <div v-if="loadingHrSchedule" class="table-skeleton">
            Загрузка графика отпусков...
          </div>

          <table v-else class="table">
            <thead>
              <tr>
                <th>Сотрудник</th>
                <th>Периоды отпусков (утвержденные)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="hrSchedule.length === 0">
                <td colspan="2" class="muted">
                  На {{ hrScheduleYear }} год согласованных отпусков пока нет
                </td>
              </tr>
              <tr v-for="row in hrSchedule" :key="row.user_id">
                <td>
                  <div class="user-cell">
                    <div class="user-name">{{ row.full_name }}</div>
                    <div class="user-login muted">{{ row.username }}</div>
                  </div>
                </td>
                <td>
                  <div class="period-chips">
                    <span v-for="p in row.periods"
                          :key="p.id"
                          class="chip chip-period">
                      {{ p.start_date }} - {{ p.end_date }} ( {{ getDaysBetween(p.start_date, p.end_date) }} дн. )
                      <span v-if="!p.confirmed_by_employee" class="chip-sub">
                        (без подтверждения сотрудника)
                      </span>
                    </span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </section>

        <section class="card">
          <div class="card-header">
            <div>
              <h3>Уведомления</h3>
              <div class="muted">Напоминания о заявках и предстоящих отпусках</div>
            </div>
          </div>

          <transition name="fade">
            <div v-if="loadingNotifications" class="loading-skeleton">
              <div class="skeleton-line"></div>
              <div class="skeleton-line"></div>
              <div class="skeleton-line short"></div>
            </div>

            <div v-else-if="notifications.length === 0" class="muted" style="padding: 12px; text-align: center;">
              Уведомлений нет
            </div>

            <ul v-else>
              <li v-for="n in notifications" :key="n.id">
                <div>
                  <span class="tag-unread" v-if="!n.is_read">Непрочитано</span>

                  <span v-if="n.type === 'vacation_reminder_14d'">
                    [Напоминание: до начала отпуска 14 дней]
                  </span>
                  <span v-else-if="n.type === 'vacation_start_today'">
                    [Сегодня начинается отпуск]
                  </span>
                  <span v-else-if="n.type === 'request_submitted'">
                    [Новая заявка на отпуск]
                  </span>
                  <span v-else-if="n.type === 'request_approved'">
                    [Заявка согласована]
                  </span>
                  <span v-else-if="n.type === 'request_rejected'">
                    [Заявка отклонена]
                  </span>
                  <span v-else-if="n.type === 'request_rescheduled'">
                    [Изменён период заявки]
                  </span>
                  <span v-else-if="n.type === 'request_confirmed'">
                    [Сотрудник ознакомился с решением]
                  </span>
                </div>

                <div class="notification-message">
                  {{ n.message }}
                </div>

                <div class="muted" style="font-size: 12px; margin: 4px 0 6px;">
                  {{ new Date(n.created_at).toLocaleString() }}
                </div>

                <button v-if="!n.is_read" class="secondary" @click="markNotificationRead(n.id)">
                  Отметить прочитанным
                </button>
              </li>
            </ul>
          </transition>
        </section>
      </div>
    </div>

    <div v-if="showProfileModal" class="modal-backdrop">
      <div class="modal">
        <h3>Редактирование профиля</h3>
        <form @submit.prevent="saveProfile">
          <label>Имя: <input type="text" v-model="profileForm.first_name" required></label>
          <label>Фамилия: <input type="text" v-model="profileForm.last_name" required></label>
          <div class="modal-actions">
            <button type="submit">Сохранить</button>
            <button type="button" class="secondary" @click="showProfileModal = false">Отмена</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
const getCookie = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return '';
};

export default {
  name: 'App',
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
      profileForm: { first_name: '', last_name: '' },
      editingRequestId: null,
      editRequestForm: { start_date: '', end_date: '' },
      hrSchedule: [],
      hrScheduleYear: new Date().getFullYear(),
      hrSelectedManagerId: '',
      hrDepartments: [],
      loadingHrSchedule: false,
      hrCalendarMonths: ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'],
      liveSyncAttached: false,
      sseSource: null,
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
    setupLiveBalanceSync() {
      if (this.liveSyncAttached || !this.user || this.user.role !== 'employee') return;
      this.liveSyncAttached = true;
      window.addEventListener('storage', this.handleBalanceBroadcast);
    },
    teardownLiveBalanceSync() {
      if (!this.liveSyncAttached) return;
      window.removeEventListener('storage', this.handleBalanceBroadcast);
      this.liveSyncAttached = false;
    },
    handleBalanceBroadcast(event) {
      if (event.key !== 'balance_sync') return;
      if (this.user && this.user.role === 'employee') {
        this.refreshEmployeeData(true);
      }
    },
    async refreshEmployeeData(silent = false) {
      await Promise.all([
        this.loadBalance(silent),
        this.fetchVacationBalances(),
        this.loadMyRequests(),
      ]);
    },
    broadcastBalanceUpdate() {
      try {
        localStorage.setItem('balance_sync', JSON.stringify({ ts: Date.now() }));
      } catch (e) {
        // ignore storage errors
      }
    },
    startSse() {
      if (this.sseSource) return;
      this.sseSource = new EventSource('/api/live/sse', { withCredentials: true });
      this.sseSource.addEventListener('change', this.onSseChange);
      this.sseSource.onerror = () => {
        this.stopSse();
        // попытка переподключения через 3 сек
        setTimeout(() => this.startSse(), 3000);
      };
    },
    stopSse() {
      if (this.sseSource) {
        this.sseSource.removeEventListener('change', this.onSseChange);
        this.sseSource.close();
        this.sseSource = null;
      }
    },
    async onSseChange(event) {
      try {
        const payload = JSON.parse(event.data || '{}');
        if (!payload || payload.type !== 'change') return;
        if (!this.user) return;
        if (this.user.role === 'employee') {
          await Promise.all([
            this.loadBalance(true),
            this.fetchVacationBalances(),
            this.loadMyRequests(true),
            this.loadNotifications(true),
            this.refreshNotifications(),
          ]);
        } else if (this.user.role === 'manager') {
          await Promise.all([
            this.loadManagerRequests(true),
            this.fetchVacationBalances(),
            this.loadNotifications(true),
            this.refreshNotifications(),
          ]);
        } else if (this.user.role === 'hr') {
          await Promise.all([
            this.loadHrRequests(true),
            this.fetchVacationBalances(),
            this.loadHrSchedule(),
            this.loadNotifications(true),
            this.refreshNotifications(),
          ]);
        }
      } catch (err) {
        console.error('SSE parse error', err);
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
        this.setupLiveBalanceSync();
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
      this.teardownLiveBalanceSync();
      this.stopSse();
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
        const prev = this.balance;
        this.balance = data.days_remaining;
        if (prev !== this.balance) {
          this.broadcastBalanceUpdate();
        }
      } catch (err) {
        console.error(err);
      } finally {
        if (!silent) {
          this.loadingEmployeeData = false;
        }
      }
    },
    async loadMyRequests(silent = false) {
      if (!silent) this.loadingEmployeeData = true;
      try {
        const data = await this.fetchJson('/api/vacation/requests/my');
        this.myRequests = data.requests;
      } catch (err) {
        console.error(err);
      } finally {
        if (!silent) this.loadingEmployeeData = false;
      }
    },
    startEditRequest(request) {
      if (!request) return;
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
        this.broadcastBalanceUpdate();
      } catch (err) {
        this.showToast(err.message || 'Не удалось обновить заявку', 'error');
      }
    },
    async deleteRequest(id) {
      if (!id) return;
      const confirmed = window.confirm('Удалить заявку? Это действие нельзя отменить.');
      if (!confirmed) return;
      try {
        await this.fetchJson(`/api/vacation/request/${id}/delete`, { method: 'POST' });
        await Promise.all([
          this.loadMyRequests(true),
          this.fetchVacationBalances(),
        ]);
        this.showToast('Заявка удалена', 'success');
        this.broadcastBalanceUpdate();
      } catch (err) {
        this.showToast(err.message || 'Не удалось удалить заявку', 'error');
      }
    },
    async duplicateRequest(id) {
      if (!id) return;
      try {
        await this.fetchJson(`/api/vacation/request/${id}/duplicate`, { method: 'POST' });
        await Promise.all([
          this.loadMyRequests(true),
          this.fetchVacationBalances(),
        ]);
        this.showToast('Заявка продублирована', 'success');
        this.broadcastBalanceUpdate();
      } catch (err) {
        this.showToast(err.message || 'Не удалось продублировать заявку', 'error');
      }
    },
    cancelEditRequest() {
      this.editingRequestId = null;
      this.editRequestForm = { start_date: '', end_date: '' };
    },
    async createRequest() {
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
        this.editingRequestId = null;

        await Promise.all([
          this.loadMyRequests(),
          this.fetchVacationBalances(),
        ]);

        this.showToast('Заявка отправлена на согласование', 'success');
        this.broadcastBalanceUpdate();
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
        this.broadcastBalanceUpdate();
      } catch (err) {
        this.showToast(err.message, 'error');
      }
    },
    async loadManagerRequests(silent = false) {
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
    async loadHrRequests(silent = false) {
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
    async loadNotifications(silent = false) {
      if (!this.user) return;
      if (!silent) this.loadingNotifications = true;
      try {
        const data = await this.fetchJson('/api/notifications');
        const raw = data.notifications || [];
        this.notifications = raw.map(n => ({
          ...n,
          display_text: this.formatNotificationText(n),
        }));
      } catch (err) {
        console.error(err);
      } finally {
        if (!silent) this.loadingNotifications = false;
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
    canModifyRequest(req) {
      return req && req.status === 'pending';
    },
    canDeleteRequest(req) {
      return req && req.status === 'pending';
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
      this.setupLiveBalanceSync();
    }
    this.startSse();
  },
  beforeUnmount() {
    this.stopSse();
  },
};
</script>

<style scoped>
.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 8px;
  gap: 4px;
}

.icon-button .icon-trash {
  display: block;
}
</style>
