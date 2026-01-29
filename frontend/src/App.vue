<template>
  <div class="container" :class="{ 'dark-theme': isDarkMode }">
    <div class="app-container">
      <!-- 侧边栏 -->
      <div class="sidebar">
        <div class="logo">📊 交易系统</div>
        
        <!-- 钱包信息区域 -->
        <div class="wallet-section">
          <!-- 钱包未连接时显示连接按钮 -->
          <div v-if="!isWalletConnected" class="wallet-connect-mini">
            <p class="connect-hint">连接钱包解锁高级功能</p>
            <button class="connect-btn" @click="showWalletModal = true">
              🔐 连接钱包
            </button>
          </div>
          
          <!-- 钱包已连接时显示用户信息 -->
          <div v-else class="wallet-info-sidebar">
            <div class="wallet-user">
              <div class="user-avatar">{{ userInfo.nickname ? userInfo.nickname[0] : '👤' }}</div>
              <div class="user-details">
                <span class="user-name">{{ userInfo.nickname || '用户' }}</span>
                <span class="user-address">{{ formatAddress(userInfo.public_key) }}</span>
              </div>
            </div>
            <button class="disconnect-btn" @click="disconnectWallet" title="断开连接">
              🚪
            </button>
          </div>
        </div>

        <ul class="nav-menu">
          <li class="nav-item">
            <a class="nav-link" :class="{ active: activeTab === 'market' }" @click="switchTab('market')">
              📈 行情数据
            </a>
          </li>
          <li class="nav-item">
            <a class="nav-link" :class="{ active: activeTab === 'strategy' }" @click="switchTab('strategy')">
              🎯 策略回测
            </a>
          </li>
          <li class="nav-item">
            <a class="nav-link" :class="{ active: activeTab === 'backtest' }" @click="switchTab('backtest')">
              🔍 完整回测
            </a>
          </li>
          <li class="nav-item">
            <a class="nav-link" :class="{ active: activeTab === 'optimize', disabled: !isWalletConnected }" 
               @click="switchTab('optimize')" 
               :title="!isWalletConnected ? '需要连接钱包' : ''">
              ⚡ 参数优化
              <span v-if="!isWalletConnected" class="lock-icon">🔒</span>
            </a>
          </li>
        </ul>
      </div>

      <!-- 主内容 -->
      <div class="main">
        <div class="header">
          <h1>{{ pageTitle }}</h1>
          <div class="header-controls">
            <button class="theme-toggle" @click="toggleTheme" :title="isDarkMode ? '切换到浅色主题' : '切换到深色主题'">
              {{ isDarkMode ? '☀️' : '🌙' }}
            </button>
            <div class="status-indicator">
              <div class="status-dot"></div>
              <span>{{ apiStatus }}</span>
            </div>
          </div>
        </div>

        <div class="content">
          <!-- 行情数据 -->
          <MarketData v-if="activeTab === 'market'" />

          <!-- 策略回测 -->
          <StrategyBacktest v-if="activeTab === 'strategy'" />

          <!-- 完整回测 -->
          <FullBacktest v-if="activeTab === 'backtest'" />

          <!-- 参数优化 -->
          <ParameterOptimize v-if="activeTab === 'optimize'" :auth-token="authToken" />
        </div>
      </div>
    </div>

    <!-- 钱包连接模态框 -->
    <div v-if="showWalletModal" class="modal-overlay" @click="showWalletModal = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>连接钱包</h2>
          <button class="close-btn" @click="showWalletModal = false">✕</button>
        </div>
        <div class="modal-body">
          <WalletConnect @connected="onWalletConnected" />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import MarketData from './components/MarketData.vue'
import StrategyBacktest from './components/StrategyBacktest.vue'
import FullBacktest from './components/FullBacktest.vue'
import ParameterOptimize from './components/ParameterOptimize.vue'
import WalletConnect from './components/WalletConnect.vue'

export default {
  components: {
    MarketData,
    StrategyBacktest,
    FullBacktest,
    ParameterOptimize,
    WalletConnect
  },
  setup() {
    const activeTab = ref('market')
    const apiStatus = ref('连接中...')
    const isWalletConnected = ref(false)
    const authToken = ref('')
    const userInfo = ref({})
    const showWalletModal = ref(false)
    const isDarkMode = ref(false)

    const pageTitle = computed(() => {
      const titles = {
        market: '📈 行情数据',
        strategy: '🎯 策略回测',
        backtest: '🔍 完整回测',
        optimize: '⚡ 参数优化'
      }
      return titles[activeTab.value] || '交易系统'
    })

    const switchTab = (tab) => {
      // 如果点击参数优化但钱包未连接，显示连接提示
      if (tab === 'optimize' && !isWalletConnected.value) {
        showWalletModal.value = true
        return
      }
      activeTab.value = tab
    }

    const checkApiHealth = async () => {
      try {
        const response = await fetch('/api/health')
        if (response.ok) {
          apiStatus.value = '✅ 正常'
        } else {
          apiStatus.value = '❌ 异常'
        }
      } catch (error) {
        apiStatus.value = '❌ 离线'
      }
    }

    const onWalletConnected = (data) => {
      isWalletConnected.value = true
      authToken.value = data.token
      userInfo.value = data.user
      showWalletModal.value = false
      
      // 连接成功后自动跳转到参数优化页面
      activeTab.value = 'optimize'
    }

    const disconnectWallet = () => {
      isWalletConnected.value = false
      authToken.value = ''
      userInfo.value = {}
      
      // 清除本地存储
      localStorage.removeItem('wallet_token')
      localStorage.removeItem('wallet_info')
      
      // 如果当前在参数优化页面，跳转到其他页面
      if (activeTab.value === 'optimize') {
        activeTab.value = 'market'
      }
    }

    const formatAddress = (address) => {
      if (!address) return ''
      return `${address.slice(0, 4)}...${address.slice(-4)}`
    }

    const toggleTheme = () => {
      isDarkMode.value = !isDarkMode.value
      localStorage.setItem('theme', isDarkMode.value ? 'dark' : 'light')
      console.log('Theme toggled:', isDarkMode.value ? 'dark' : 'light')
    }

    // 检查本地存储的认证信息
    const checkStoredAuth = async () => {
      const storedToken = localStorage.getItem('wallet_token')
      const storedInfo = localStorage.getItem('wallet_info')

      if (storedToken && storedInfo) {
        try {
          // 验证token是否仍然有效
          const response = await fetch('/api/auth/verify', {
            headers: {
              'Authorization': `Bearer ${storedToken}`
            }
          })

          if (response.ok) {
            authToken.value = storedToken
            userInfo.value = JSON.parse(storedInfo)
            isWalletConnected.value = true
          } else {
            // Token无效，清除存储
            localStorage.removeItem('wallet_token')
            localStorage.removeItem('wallet_info')
          }
        } catch (err) {
          console.error('验证存储的认证信息失败:', err)
          localStorage.removeItem('wallet_token')
          localStorage.removeItem('wallet_info')
        }
      }
    }

    onMounted(() => {
      checkApiHealth()
      setInterval(checkApiHealth, 5000)
      checkStoredAuth()
      
      // 初始化主题
      const savedTheme = localStorage.getItem('theme')
      if (savedTheme === 'dark') {
        isDarkMode.value = true
      } else {
        isDarkMode.value = false
      }
      console.log('Theme initialized:', isDarkMode.value ? 'dark' : 'light')
    })

    return {
      activeTab,
      pageTitle,
      apiStatus,
      isWalletConnected,
      authToken,
      userInfo,
      showWalletModal,
      isDarkMode,
      switchTab,
      onWalletConnected,
      disconnectWallet,
      formatAddress,
      toggleTheme
    }
  }
}
</script>

<style scoped>
/* 基础样式 */
.container {
  display: flex;
  height: 100vh;
  background: #f5f5f5;
  transition: all 0.3s ease;
}

.app-container {
  display: flex;
  width: 100%;
  margin: 0;
  padding: 0;
}

.sidebar {
  width: 280px;
  background: white;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  position: relative;
  height: 100vh;
  overflow-y: auto;
  transition: all 0.3s ease;
}

.logo {
  padding: 1.5rem;
  font-size: 1.5rem;
  font-weight: bold;
  color: #333;
  border-bottom: 1px solid #e0e0e0;
  transition: all 0.3s ease;
}

.wallet-section {
  border-bottom: 1px solid #e0e0e0;
}

.wallet-connect-mini {
  padding: 1rem;
  text-align: center;
}

.connect-hint {
  font-size: 0.85rem;
  color: #666;
  margin: 0 0 0.75rem 0;
}

.connect-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: transform 0.2s ease;
}

.connect-btn:hover {
  transform: translateY(-1px);
}

.wallet-info-sidebar {
  padding: 1rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.wallet-user {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  font-size: 1rem;
}

.user-details {
  display: flex;
  flex-direction: column;
}

.user-name {
  font-weight: 500;
  color: #333;
  font-size: 0.9rem;
}

.user-address {
  font-size: 0.8rem;
  color: #666;
  font-family: monospace;
}

.disconnect-btn {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 4px;
  transition: background 0.3s ease;
}

.disconnect-btn:hover {
  background: #f0f0f0;
}

.nav-menu {
  list-style: none;
  padding: 0;
  margin: 0;
  flex: 1;
}

.nav-item {
  border-bottom: 1px solid #f0f0f0;
}

.nav-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  color: #666;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.3s ease;
}

.nav-link:hover:not(.disabled) {
  background: #f8f9fa;
  color: #333;
}

.nav-link.active {
  background: #007bff;
  color: white;
}

.nav-link.disabled {
  color: #ccc;
  cursor: not-allowed;
}

.lock-icon {
  font-size: 0.8rem;
  opacity: 0.7;
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 100vh;
  margin: 0;
  padding: 0;
}

.header {
  background: white;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
  transition: all 0.3s ease;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.theme-toggle {
  background: none;
  border: 2px solid #e0e0e0;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  cursor: pointer;
  font-size: 1.2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.theme-toggle:hover {
  border-color: #007bff;
  transform: scale(1.1);
}

.header h1 {
  margin: 0;
  color: #333;
  font-size: 1.5rem;
  transition: all 0.3s ease;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: #666;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #28a745;
  animation: pulse 2s infinite;
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 0;
  background: #f5f5f5;
  margin: 0;
  transition: all 0.3s ease;
}

/* 深色主题样式 - 科技蓝配色 */
.container.dark-theme {
  background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1419 100%);
  color: #e1f5fe;
  position: relative;
}

.container.dark-theme::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image: 
    linear-gradient(rgba(0, 188, 212, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 188, 212, 0.03) 1px, transparent 1px);
  background-size: 50px 50px;
  pointer-events: none;
  z-index: -1;
}

.dark-theme .sidebar {
  background: linear-gradient(180deg, #0d1421 0%, #1a2332 100%);
  border-right: 1px solid #00bcd4;
  box-shadow: 2px 0 10px rgba(0, 188, 212, 0.1);
}

.dark-theme .logo {
  color: #00e5ff;
  text-shadow: 0 0 10px rgba(0, 229, 255, 0.3);
}

.dark-theme .nav-link {
  color: #b3e5fc;
}

.dark-theme .nav-link:hover:not(.disabled) {
  background: linear-gradient(90deg, rgba(0, 188, 212, 0.1) 0%, rgba(0, 229, 255, 0.05) 100%);
  color: #00e5ff;
  border-left: 3px solid #00bcd4;
  transform: translateX(3px);
}

.dark-theme .nav-link.active {
  background: linear-gradient(90deg, #00bcd4 0%, #0097a7 100%);
  color: #ffffff;
  box-shadow: 0 2px 10px rgba(0, 188, 212, 0.3);
}

.dark-theme .header {
  background: linear-gradient(90deg, #0d1421 0%, #1a2332 100%);
  border-bottom: 2px solid #00bcd4;
  box-shadow: 0 2px 20px rgba(0, 188, 212, 0.1);
}

.dark-theme .header h1 {
  color: #00e5ff;
  text-shadow: 0 0 10px rgba(0, 229, 255, 0.2);
}

.dark-theme .theme-toggle {
  border: 2px solid #00bcd4;
  color: #00e5ff;
  background: rgba(0, 188, 212, 0.1);
  box-shadow: 0 0 10px rgba(0, 188, 212, 0.2);
}

.dark-theme .theme-toggle:hover {
  border-color: #00e5ff;
  background: rgba(0, 229, 255, 0.2);
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.4);
}

.dark-theme .content {
  background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1419 100%);
}

.dark-theme .status-dot {
  background: #00e5ff;
  animation: pulse-tech 2s infinite;
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.5);
}

.dark-theme .status-indicator {
  color: #b3e5fc;
}

.dark-theme .wallet-connect-mini {
  background: linear-gradient(135deg, #0d1421 0%, #1a2332 100%);
  border: 1px solid #00bcd4;
  border-radius: 8px;
}

.dark-theme .connect-hint {
  color: #81d4fa;
}

.dark-theme .wallet-info-sidebar {
  background: linear-gradient(135deg, #0d1421 0%, #1a2332 100%);
  border: 1px solid #00bcd4;
  border-radius: 8px;
}

.dark-theme .user-name {
  color: #00e5ff;
}

.dark-theme .user-address {
  color: #81d4fa;
}

.dark-theme .disconnect-btn:hover {
  background: rgba(0, 188, 212, 0.2);
}

.dark-theme .modal-content {
  background: linear-gradient(135deg, #0d1421 0%, #1a2332 100%);
  border: 1px solid #00bcd4;
  box-shadow: 0 10px 40px rgba(0, 188, 212, 0.2);
}

.dark-theme .modal-header {
  border-bottom: 1px solid #00bcd4;
}

.dark-theme .modal-header h2 {
  color: #00e5ff;
  text-shadow: 0 0 10px rgba(0, 229, 255, 0.2);
}

.dark-theme .close-btn {
  color: #81d4fa;
}

.dark-theme .close-btn:hover {
  background: rgba(0, 188, 212, 0.2);
  color: #00e5ff;
}

/* 动画效果 */
@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(40, 167, 69, 0.7);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(40, 167, 69, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(40, 167, 69, 0);
  }
}

@keyframes pulse-tech {
  0% {
    box-shadow: 0 0 0 0 rgba(0, 229, 255, 0.7);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(0, 229, 255, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(0, 229, 255, 0);
  }
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  transition: all 0.3s ease;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h2 {
  margin: 0;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
  padding: 0.25rem;
  border-radius: 4px;
  transition: background 0.3s ease;
}

.close-btn:hover {
  background: #f0f0f0;
}

.modal-body {
  padding: 0;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .sidebar {
    width: 240px;
  }
  
  .content {
    padding: 0.75rem;
  }
}

@media (max-width: 600px) {
  .sidebar {
    width: 200px;
  }
  
  .content {
    padding: 0.5rem;
  }
}
</style>
/* 全局深色主题样式 - 确保子组件正确显示 */
.dark-theme :deep(.card) {
  background: linear-gradient(135deg, #0d1421 0%, #1a2332 100%) !important;
  border: 1px solid #00bcd4 !important;
  color: #e1f5fe !important;
  box-shadow: 0 4px 20px rgba(0, 188, 212, 0.1) !important;
}

.dark-theme :deep(.card h2),
.dark-theme :deep(.card h3) {
  color: #00e5ff !important;
  text-shadow: 0 0 10px rgba(0, 229, 255, 0.2) !important;
}

.dark-theme :deep(.form-group label) {
  color: #b3e5fc !important;
}

.dark-theme :deep(.form-group input),
.dark-theme :deep(.form-group select) {
  background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%) !important;
  border: 2px solid #00bcd4 !important;
  color: #e1f5fe !important;
  box-shadow: inset 0 2px 10px rgba(0, 188, 212, 0.1) !important;
}

.dark-theme :deep(.form-group input:focus),
.dark-theme :deep(.form-group select:focus) {
  border-color: #00e5ff !important;
  box-shadow: 0 0 20px rgba(0, 229, 255, 0.3) !important;
}

.dark-theme :deep(.btn-primary) {
  background: linear-gradient(135deg, #00bcd4 0%, #0097a7 100%) !important;
  border: none !important;
  box-shadow: 0 4px 15px rgba(0, 188, 212, 0.3) !important;
  color: white !important;
}

.dark-theme :deep(.btn-primary:hover) {
  background: linear-gradient(135deg, #00e5ff 0%, #00bcd4 100%) !important;
  box-shadow: 0 6px 25px rgba(0, 229, 255, 0.4) !important;
  transform: translateY(-2px) !important;
}

.dark-theme :deep(.btn-secondary) {
  background: linear-gradient(135deg, #263238 0%, #37474f 100%) !important;
  border: 1px solid #00bcd4 !important;
  color: #b3e5fc !important;
}

.dark-theme :deep(.btn-secondary:hover) {
  background: linear-gradient(135deg, #37474f 0%, #455a64 100%) !important;
  border-color: #00e5ff !important;
  color: #00e5ff !important;
}

.dark-theme :deep(.stat-card) {
  background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%) !important;
  border: 1px solid #00bcd4 !important;
  box-shadow: 0 2px 15px rgba(0, 188, 212, 0.1) !important;
}

.dark-theme :deep(.stat-label) {
  color: #81d4fa !important;
}

.dark-theme :deep(.stat-value) {
  color: #00e5ff !important;
  text-shadow: 0 0 5px rgba(0, 229, 255, 0.2) !important;
}

.dark-theme :deep(.stat-value.positive) {
  color: #4caf50 !important;
}

.dark-theme :deep(.stat-value.negative) {
  color: #f44336 !important;
}

.dark-theme :deep(.chart-container) {
  background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%) !important;
  border: 1px solid #00bcd4 !important;
  box-shadow: 0 4px 20px rgba(0, 188, 212, 0.1) !important;
}

.dark-theme :deep(table) {
  background: linear-gradient(135deg, #0d1421 0%, #1a2332 100%) !important;
  border: 1px solid #00bcd4 !important;
}

.dark-theme :deep(table th) {
  background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%) !important;
  color: #b3e5fc !important;
  border-bottom: 2px solid #00bcd4 !important;
}

.dark-theme :deep(table td) {
  color: #e1f5fe !important;
  border-bottom: 1px solid #00bcd4 !important;
}

.dark-theme :deep(tbody tr:hover) {
  background: linear-gradient(90deg, rgba(0, 188, 212, 0.1) 0%, rgba(0, 229, 255, 0.05) 100%) !important;
}

.dark-theme :deep(.message.success) {
  background: linear-gradient(135deg, #004d40 0%, #00695c 100%) !important;
  color: #4dd0e1 !important;
  border: 1px solid #00bcd4 !important;
}

.dark-theme :deep(.message.error) {
  background: linear-gradient(135deg, #b71c1c 0%, #d32f2f 100%) !important;
  color: #ffcdd2 !important;
  border: 1px solid #f44336 !important;
}

.dark-theme :deep(.loading-text) {
  color: #00e5ff !important;
}

.dark-theme :deep(.price-preview-section),
.dark-theme :deep(.manual-price-section),
.dark-theme :deep(.chart-selection-section) {
  background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%) !important;
  border: 1px solid #00bcd4 !important;
  box-shadow: 0 2px 15px rgba(0, 188, 212, 0.1) !important;
}

.dark-theme :deep(.stat-item),
.dark-theme :deep(.range-item) {
  background: linear-gradient(135deg, #0d1421 0%, #1a2332 100%) !important;
  border: 1px solid #00bcd4 !important;
}

.dark-theme :deep(.stat-item .label),
.dark-theme :deep(.range-item .label) {
  color: #81d4fa !important;
}

.dark-theme :deep(.stat-item .value),
.dark-theme :deep(.range-item .value) {
  color: #e1f5fe !important;
}
/* 图表容器样式修复 */
.dark-theme :deep(.chart-container) {
  background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%) !important;
  border: 1px solid #00bcd4 !important;
  box-shadow: 0 4px 20px rgba(0, 188, 212, 0.1) !important;
  border-radius: 12px !important;
  padding: 1rem !important;
}

.dark-theme :deep(#equityChart) {
  background: transparent !important;
}

/* 确保canvas在深色主题下可见 */
.dark-theme :deep(canvas) {
  background: transparent !important;
  border-radius: 8px !important;
}

/* 图表标题样式 */
.dark-theme :deep(.chart-container h3) {
  color: #00e5ff !important;
  text-shadow: 0 0 10px rgba(0, 229, 255, 0.2) !important;
  margin-bottom: 1rem !important;
}

/* 修复图表在深色主题下的显示问题 */
.chart-container {
  background: white;
  border-radius: 12px;
  padding: 1rem;
  margin: 1rem 0;
  border: 1px solid #e0e0e0;
  min-height: 450px;
}

.chart-container h3 {
  margin: 0 0 1rem 0;
  color: #333;
  font-size: 1.1rem;
}

/* 确保图表容器有足够的高度 */
.chart-container canvas {
  max-width: 100% !important;
  height: 400px !important;
}