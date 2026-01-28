<template>
  <div class="container">
    <!-- 侧边栏 -->
    <div class="sidebar">
      <div class="logo">📊 交易系统</div>
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
          <a class="nav-link" :class="{ active: activeTab === 'optimize' }" @click="switchTab('optimize')">
            ⚡ 参数优化
          </a>
        </li>
      </ul>
    </div>

    <!-- 主内容 -->
    <div class="main">
      <div class="header">
        <h1>{{ pageTitle }}</h1>
        <div class="status-indicator">
          <div class="status-dot"></div>
          <span>{{ apiStatus }}</span>
        </div>
      </div>

      <!-- 行情数据 -->
      <MarketData v-if="activeTab === 'market'" />

      <!-- 策略回测 -->
      <StrategyBacktest v-if="activeTab === 'strategy'" />

      <!-- 完整回测 -->
      <FullBacktest v-if="activeTab === 'backtest'" />

      <!-- 参数优化 -->
      <ParameterOptimize v-if="activeTab === 'optimize'" />
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import MarketData from './components/MarketData.vue'
import StrategyBacktest from './components/StrategyBacktest.vue'
import FullBacktest from './components/FullBacktest.vue'
import ParameterOptimize from './components/ParameterOptimize.vue'

export default {
  components: {
    MarketData,
    StrategyBacktest,
    FullBacktest,
    ParameterOptimize
  },
  setup() {
    const activeTab = ref('market')
    const apiStatus = ref('连接中...')

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

    onMounted(() => {
      checkApiHealth()
      setInterval(checkApiHealth, 5000)
    })

    return {
      activeTab,
      pageTitle,
      apiStatus,
      switchTab
    }
  }
}
</script>
