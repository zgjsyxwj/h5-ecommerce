<script setup>
import { ref, computed, onMounted } from 'vue'
import CsrPanel from './components/CsrPanel.vue'

const API_BASE = 'http://localhost:8001'
const USERNAME_REGEX = /^[a-zA-Z0-9一-龥_]{1,20}$/
const KNOWN_USERS = ['alex', 'tom', 'jerry']

const products = ref([])
const loadError = ref(false)
const loaded = ref(false)

const username = ref('')
const usernameInput = ref('')
const isLoggedIn = computed(() => username.value.length > 0)

const panelOpen = ref(false)

const showSuggestions = ref(false)
const activeIdx = ref(-1)
const suggestions = computed(() => {
  const q = usernameInput.value.trim().toLowerCase()
  if (!q) return KNOWN_USERS
  return KNOWN_USERS.filter(u => u.toLowerCase().startsWith(q))
})

function handleInputFocus() {
  showSuggestions.value = true
  activeIdx.value = -1
}
let blurTimer = null
function handleInputBlur() {
  // delay so mousedown on suggestion can fire first
  blurTimer = setTimeout(() => { showSuggestions.value = false }, 140)
}
function handleInputChange() {
  showSuggestions.value = true
  activeIdx.value = -1
}
function pickSuggestion(name) {
  if (blurTimer) clearTimeout(blurTimer)
  usernameInput.value = name
  showSuggestions.value = false
  activeIdx.value = -1
}
function handleArrow(dir) {
  if (!showSuggestions.value || suggestions.value.length === 0) return
  const len = suggestions.value.length
  activeIdx.value = (activeIdx.value + dir + len) % len
}
function handleEnter() {
  if (showSuggestions.value && activeIdx.value >= 0) {
    pickSuggestion(suggestions.value[activeIdx.value])
    return
  }
  handleLogin()
}

const toastMessage = ref('')
let toastTimer = null
function showToast(msg) {
  toastMessage.value = msg
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastMessage.value = '' }, 3000)
}

const formatPrice = (s) => {
  const [int, dec] = String(s).split('.')
  return { int: int.replace(/\B(?=(\d{3})+(?!\d))/g, ','), dec: dec ?? '00' }
}

onMounted(async () => {
  try {
    username.value = localStorage.getItem('username') || ''
  } catch (_) { /* localStorage unavailable */ }

  try {
    const res = await fetch(`${API_BASE}/api/products`)
    if (!res.ok) throw new Error(`status ${res.status}`)
    products.value = await res.json()
  } catch (_) {
    loadError.value = true
  } finally {
    loaded.value = true
  }
})

function handleLogin() {
  const value = usernameInput.value.trim()
  if (!USERNAME_REGEX.test(value)) {
    showToast('用户名长度需为 1–20 位，仅允许字母、数字、中文、下划线')
    return
  }
  try {
    localStorage.setItem('username', value)
  } catch (_) {
    showToast('无法保存登录状态，请检查浏览器设置')
    return
  }
  username.value = value
  usernameInput.value = ''
}

function handleLogout() {
  try { localStorage.removeItem('username') } catch (_) { /* ignore */ }
  username.value = ''
}

function handleCsrClick() {
  if (!isLoggedIn.value) {
    showToast('请先登录后再咨询客服')
    return
  }
  panelOpen.value = true
}
</script>

<template>
  <div class="app">
    <header class="masthead">
      <a href="/" class="brand" aria-label="AI 编程联盟·h5商城">
        <span class="brand-mark">AI 编程联盟</span>
        <span class="brand-dot" aria-hidden>·</span>
        <span class="brand-word">h5商城</span>
      </a>

      <div class="auth">
        <template v-if="isLoggedIn">
          <span class="auth-status">
            <span class="auth-dot" aria-hidden></span>
            <span class="auth-name">{{ username }}</span>
          </span>
          <button class="link-btn" @click="handleLogout">退出</button>
        </template>
        <template v-else>
          <div class="auth-field">
            <input
              v-model="usernameInput"
              class="auth-input"
              type="text"
              placeholder="输入用户名"
              aria-label="用户名"
              autocomplete="off"
              role="combobox"
              :aria-expanded="showSuggestions"
              aria-controls="user-suggest"
              @focus="handleInputFocus"
              @blur="handleInputBlur"
              @input="handleInputChange"
              @keydown.down.prevent="handleArrow(1)"
              @keydown.up.prevent="handleArrow(-1)"
              @keydown.esc="showSuggestions = false"
              @keydown.enter.prevent="handleEnter"
            />
            <transition name="suggest">
              <ul
                v-if="showSuggestions && suggestions.length"
                id="user-suggest"
                class="suggest"
                role="listbox"
              >
                <li class="suggest-head">演示账号</li>
                <li
                  v-for="(u, i) in suggestions"
                  :key="u"
                  class="suggest-item"
                  :class="{ 'is-active': i === activeIdx }"
                  role="option"
                  :aria-selected="i === activeIdx"
                  @mousedown.prevent="pickSuggestion(u)"
                  @mouseenter="activeIdx = i"
                >
                  <span class="suggest-name">{{ u }}</span>
                  <span class="suggest-hint">↩</span>
                </li>
              </ul>
            </transition>
          </div>
          <button class="auth-btn" @click="handleLogin">登录</button>
        </template>
      </div>
    </header>

    <main class="main">
      <p v-if="loadError" class="error">商品加载失败，请稍后重试</p>

      <ul v-else-if="loaded" class="grid is-stagger">
        <li
          v-for="(p, i) in products"
          :key="p.id"
          class="card"
          :style="{ '--i': i }"
        >
          <div class="thumb">
            <img :src="p.image_url" :alt="p.name" loading="lazy" />
          </div>
          <div class="body">
            <h3 class="name">{{ p.name }}</h3>
            <div class="meta">
              <span class="price">
                <span class="price-glyph">¥</span><span class="price-int">{{ formatPrice(p.price).int }}</span><span class="price-dec">.{{ formatPrice(p.price).dec }}</span>
              </span>
              <span class="stock">剩余 {{ p.stock }} 件</span>
            </div>
          </div>
        </li>
      </ul>

      <div v-else class="grid skel" aria-hidden>
        <div v-for="n in 8" :key="n" class="card card--skel"></div>
      </div>
    </main>

    <button
      class="csr-fab"
      type="button"
      title="智能客服"
      aria-label="智能客服"
      @click="handleCsrClick"
    >
      <svg class="csr-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M5 5h12a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-6.5L7 19v-3H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z"
          fill="none"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linejoin="round"
        />
        <circle cx="9"  cy="10.5" r="0.9" fill="currentColor"/>
        <circle cx="13" cy="10.5" r="0.9" fill="currentColor"/>
      </svg>
      <span class="csr-pulse" aria-hidden></span>
    </button>

    <CsrPanel
      v-model:open="panelOpen"
      :username="username"
      :api-base="API_BASE"
    />

    <transition name="toast">
      <div v-if="toastMessage" class="toast" role="status" aria-live="polite">
        <span class="toast-bar" aria-hidden></span>
        <span class="toast-text">{{ toastMessage }}</span>
      </div>
    </transition>
  </div>
</template>

<style>
:root {
  --paper:      oklch(96.6% 0.006 85);
  --paper-2:    oklch(94.5% 0.008 85);
  --surface:    oklch(99.2% 0.002 85);
  --ink:        oklch(20% 0.014 240);
  --ink-2:      oklch(42% 0.012 240);
  --ink-3:      oklch(60% 0.008 240);
  --rule:       oklch(88% 0.006 240);
  --rule-soft:  oklch(91% 0.005 240);
  --accent:     oklch(38% 0.085 152);

  --space-1:  4px;
  --space-2:  8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --space-7: 48px;
  --space-8: 64px;

  --type-body: 'Hanken Grotesk', -apple-system, BlinkMacSystemFont,
               'PingFang SC', 'HarmonyOS Sans SC', 'Microsoft YaHei',
               'Helvetica Neue', sans-serif;

  --ease-out: cubic-bezier(0.22, 1, 0.36, 1);
}

* { box-sizing: border-box; margin: 0; padding: 0; }
html { background: var(--paper); }
body {
  font-family: var(--type-body);
  background: var(--paper);
  color: var(--ink);
  font-size: 15px;
  line-height: 1.5;
  font-feature-settings: 'tnum';
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}
button, input { font: inherit; color: inherit; }
button { cursor: pointer; background: transparent; border: 0; }
a { color: inherit; text-decoration: none; }

.app {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 var(--space-4);
  padding-bottom: var(--space-8);
}

/* ───────── masthead (single row) ───────── */
.masthead {
  display: flex; align-items: center; justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4) 0;
  margin-bottom: var(--space-5);
  border-bottom: 1px solid var(--rule);
  position: sticky; top: 0; z-index: 10;
  background: var(--paper);
  backdrop-filter: saturate(140%);
}
.brand {
  display: inline-flex; align-items: baseline; gap: 8px;
  letter-spacing: -0.005em;
  flex-shrink: 0;
}
.brand-mark { font-weight: 700; font-size: 16px; color: var(--ink); }
.brand-dot { color: var(--rule); font-size: 14px; }
.brand-word { font-weight: 400; font-size: 14px; color: var(--ink-2); }

.auth {
  display: inline-flex; align-items: center; gap: var(--space-3);
  font-size: 13px;
  min-width: 0;
}
.auth-field {
  position: relative;
  display: inline-block;
}
.auth-input {
  border: 1px solid var(--rule);
  background: var(--surface);
  padding: 7px 12px;
  color: var(--ink);
  outline: none;
  border-radius: 4px;
  width: 200px;
  max-width: 44vw;
  transition: border-color 150ms var(--ease-out);
}
.auth-input::placeholder { color: var(--ink-3); }
.auth-input:focus { border-color: var(--accent); }

.suggest {
  position: absolute;
  top: calc(100% + 4px); left: 0;
  width: 100%;
  min-width: 200px;
  list-style: none;
  background: var(--surface);
  border: 1px solid var(--rule);
  border-radius: 4px;
  padding: 4px 0;
  box-shadow: 0 1px 0 var(--rule-soft), 0 14px 32px -14px rgba(20, 24, 32, 0.16);
  z-index: 30;
  overflow: hidden;
}
.suggest-head {
  padding: 6px 12px 4px;
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink-3);
}
.suggest-item {
  padding: 7px 12px;
  font-size: 13px;
  color: var(--ink);
  display: flex; align-items: center; justify-content: space-between;
  cursor: pointer;
  transition: background 120ms var(--ease-out), color 120ms var(--ease-out);
}
.suggest-item:hover,
.suggest-item.is-active {
  background: var(--paper);
}
.suggest-item.is-active .suggest-hint { color: var(--accent); }
.suggest-name { font-weight: 500; }
.suggest-hint {
  font-size: 11px;
  color: var(--ink-3);
  font-feature-settings: 'tnum';
}
.suggest-enter-active, .suggest-leave-active {
  transition: opacity 160ms var(--ease-out), transform 160ms var(--ease-out);
}
.suggest-enter-from, .suggest-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
.auth-btn {
  background: var(--ink);
  color: var(--paper);
  padding: 7px 16px;
  border-radius: 4px;
  font-weight: 500;
  letter-spacing: 0.01em;
  transition: background 160ms var(--ease-out);
}
.auth-btn:hover { background: var(--accent); }
.auth-status {
  display: inline-flex; align-items: center; gap: 6px;
  color: var(--ink);
}
.auth-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent);
}
.auth-name {
  max-width: 140px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.link-btn {
  color: var(--ink-3);
  padding: 4px 0;
  transition: color 150ms var(--ease-out);
}
.link-btn:hover { color: var(--ink); }

/* ───────── grid ───────── */
.grid {
  list-style: none;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
}
@media (min-width: 720px) {
  .grid { grid-template-columns: repeat(3, 1fr); gap: var(--space-5); }
}
@media (min-width: 1024px) {
  .grid { grid-template-columns: repeat(4, 1fr); }
}

.card {
  background: var(--surface);
  border-radius: 6px;
  overflow: hidden;
  display: flex; flex-direction: column;
  opacity: 0; transform: translateY(8px);
  transition: transform 240ms var(--ease-out);
}
.is-stagger .card {
  animation: enter 460ms var(--ease-out) both;
  animation-delay: calc(var(--i) * 50ms + 60ms);
}
@keyframes enter {
  to { opacity: 1; transform: translateY(0); }
}
.card:hover { transform: translateY(-2px); }

.thumb {
  width: 100%;
  aspect-ratio: 1 / 1;
  overflow: hidden;
  background: var(--paper-2);
}
.thumb img {
  width: 100%; height: 100%; object-fit: cover; display: block;
  transition: transform 700ms var(--ease-out);
}
.card:hover .thumb img { transform: scale(1.04); }

.body {
  padding: var(--space-3);
  display: flex; flex-direction: column; gap: 6px;
}
.name {
  font-size: 14px;
  font-weight: 500;
  color: var(--ink);
  letter-spacing: -0.005em;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 2.7em;
}
.meta {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: var(--space-2);
  margin-top: 2px;
}
.price {
  color: var(--ink);
  display: inline-flex; align-items: baseline;
}
.price-glyph { font-size: 11px; color: var(--ink-3); margin-right: 2px; }
.price-int { font-size: 16px; font-weight: 600; }
.price-dec { font-size: 12px; color: var(--ink-3); }
.stock {
  font-size: 11px;
  color: var(--ink-3);
  letter-spacing: 0.02em;
}

/* ───────── skeleton ───────── */
.skel .card--skel {
  background: var(--paper-2);
  height: 280px;
  opacity: 0.55;
  animation: skel-pulse 1.6s var(--ease-out) infinite;
}
@keyframes skel-pulse {
  50% { opacity: 0.32; }
}

/* ───────── error ───────── */
.error {
  text-align: center;
  color: var(--ink-3);
  padding: var(--space-8) 0;
  font-size: 14px;
}

/* ───────── csr floating action button ───────── */
.csr-fab {
  position: fixed;
  right: var(--space-5);
  bottom: var(--space-5);
  width: 52px; height: 52px;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--ink);
  color: var(--paper);
  border-radius: 8px;
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.06) inset,
    0 16px 36px -14px rgba(20, 24, 32, 0.45),
    0 4px 10px -4px rgba(20, 24, 32, 0.2);
  transition:
    transform 200ms var(--ease-out),
    background 200ms var(--ease-out),
    box-shadow 200ms var(--ease-out);
  z-index: 20;
}
.csr-fab:hover {
  background: var(--accent);
  transform: translateY(-2px);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.06) inset,
    0 22px 42px -16px rgba(20, 24, 32, 0.5),
    0 6px 14px -6px rgba(20, 24, 32, 0.25);
}
.csr-fab:active { transform: translateY(0); }
.csr-fab:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}
.csr-icon {
  width: 22px; height: 22px;
  display: block;
}
.csr-pulse {
  position: absolute;
  top: 6px; right: 6px;
  width: 8px; height: 8px;
  background: var(--accent);
  border: 2px solid var(--ink);
  border-radius: 50%;
  box-sizing: content-box;
}
.csr-pulse::after {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 50%;
  border: 1px solid var(--accent);
  opacity: 0.5;
  animation: csr-pulse 2.4s var(--ease-out) infinite;
}
.csr-fab:hover .csr-pulse { border-color: var(--accent); }
@keyframes csr-pulse {
  0%   { transform: scale(0.7); opacity: 0.6; }
  100% { transform: scale(2.0); opacity: 0; }
}

/* ───────── toast ───────── */
.toast {
  position: fixed; left: 50%; bottom: 90px;
  transform: translateX(-50%);
  display: flex; align-items: stretch;
  background: var(--ink);
  color: var(--paper);
  font-size: 13px;
  letter-spacing: 0.02em;
  max-width: calc(100% - 32px);
  border-radius: 4px;
  overflow: hidden;
  box-shadow: 0 14px 40px -16px rgba(20, 24, 32, 0.34);
  z-index: 30;
}
.toast-bar { width: 3px; background: var(--accent); flex-shrink: 0; }
.toast-text { padding: 11px 16px 11px 14px; }

.toast-enter-active, .toast-leave-active {
  transition: opacity 220ms var(--ease-out), transform 220ms var(--ease-out);
}
.toast-enter-from, .toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(8px);
}

/* ───────── small screens ───────── */
@media (max-width: 480px) {
  .app { padding: 0 var(--space-3); padding-bottom: var(--space-8); }
  .masthead { padding: var(--space-3) 0; gap: var(--space-2); }
  .brand-mark { font-size: 14px; }
  .brand-word { font-size: 13px; }
  .auth-input { width: 130px; padding: 6px 10px; }
  .auth-btn { padding: 6px 12px; }
  .csr-fab { right: var(--space-4); bottom: var(--space-4); width: 48px; height: 48px; }
}

/* ───────── reduced motion ───────── */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important;
    transition-duration: 0.001ms !important;
  }
  .card { opacity: 1; transform: none; }
}
</style>
