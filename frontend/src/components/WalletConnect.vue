<template>
  <div class="wallet-connect">
    <!-- 未连接状态 -->
    <div v-if="!isConnected" class="connect-section">
      <div class="wallet-header">
        <h2>🔐 钱包登录</h2>
        <p>连接您的 Solana 钱包以使用交易系统</p>
      </div>
      
      <div class="wallet-options">
        <button 
          class="wallet-btn phantom-btn"
          @click="connectPhantom"
          :disabled="connecting"
        >
          <span class="wallet-icon">👻</span>
          <span>{{ connecting ? '连接中...' : 'Phantom 钱包' }}</span>
        </button>
        
        <button 
          class="wallet-btn solflare-btn"
          @click="connectSolflare"
          :disabled="connecting"
        >
          <span class="wallet-icon">🔥</span>
          <span>{{ connecting ? '连接中...' : 'Solflare 钱包' }}</span>
        </button>
      </div>
      
      <div v-if="error" class="error-message">
        ❌ {{ error }}
      </div>
    </div>
    
    <!-- 已连接状态 -->
    <div v-else class="connected-section">
      <div class="wallet-info">
        <div class="wallet-avatar">
          <div class="avatar-circle">{{ walletInfo.nickname ? walletInfo.nickname[0] : '👤' }}</div>
        </div>
        <div class="wallet-details">
          <h3>{{ walletInfo.nickname || '用户' }}</h3>
          <p class="wallet-address">{{ formatAddress(walletInfo.public_key) }}</p>
          <span class="status-badge">✅ 已认证</span>
        </div>
      </div>
      
      <div class="wallet-actions">
        <button class="btn-secondary" @click="copyAddress">
          📋 复制地址
        </button>
        <button class="btn-danger" @click="disconnect">
          🚪 断开连接
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'

export default {
  name: 'WalletConnect',
  emits: ['connected', 'disconnected'],
  setup(props, { emit }) {
    const isConnected = ref(false)
    const connecting = ref(false)
    const walletInfo = ref({})
    const error = ref('')
    const authToken = ref('')

    // 检查钱包是否已安装
    const checkWalletInstalled = (walletName) => {
      if (walletName === 'phantom') {
        return window.solana && window.solana.isPhantom
      } else if (walletName === 'solflare') {
        return window.solflare && window.solflare.isSolflare
      }
      return false
    }

    // 连接 Phantom 钱包
    const connectPhantom = async () => {
      if (!checkWalletInstalled('phantom')) {
        error.value = '请先安装 Phantom 钱包扩展'
        return
      }
      
      await connectWallet(window.solana, 'Phantom')
    }

    // 连接 Solflare 钱包
    const connectSolflare = async () => {
      if (!checkWalletInstalled('solflare')) {
        error.value = '请先安装 Solflare 钱包扩展'
        return
      }
      
      await connectWallet(window.solflare, 'Solflare')
    }

    // 通用钱包连接逻辑
    const connectWallet = async (walletProvider, walletName) => {
      try {
        connecting.value = true
        error.value = ''

        // 连接钱包
        const response = await walletProvider.connect()
        const publicKey = response.publicKey.toString()

        console.log(`${walletName} 钱包已连接:`, publicKey)

        // 获取认证挑战
        const challengeResponse = await fetch('/api/auth/challenge', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            public_key: publicKey
          })
        })

        if (!challengeResponse.ok) {
          throw new Error('获取认证挑战失败')
        }

        const challengeData = await challengeResponse.json()
        const message = challengeData.message

        // 签名消息
        const encodedMessage = new TextEncoder().encode(message)
        const signedMessage = await walletProvider.signMessage(encodedMessage, 'utf8')
        
        // Base64 编码签名
        const signature = btoa(String.fromCharCode(...signedMessage.signature))

        // 发送登录请求
        const loginResponse = await fetch('/api/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            public_key: publicKey,
            message: message,
            signature: signature
          })
        })

        if (!loginResponse.ok) {
          const errorData = await loginResponse.json()
          throw new Error(errorData.error || '登录失败')
        }

        const loginData = await loginResponse.json()
        
        // 保存认证信息
        authToken.value = loginData.token
        walletInfo.value = loginData.user
        isConnected.value = true
        
        // 保存到本地存储
        localStorage.setItem('wallet_token', loginData.token)
        localStorage.setItem('wallet_info', JSON.stringify(loginData.user))

        emit('connected', {
          token: loginData.token,
          user: loginData.user
        })

      } catch (err) {
        console.error('钱包连接失败:', err)
        error.value = err.message || '钱包连接失败'
      } finally {
        connecting.value = false
      }
    }

    // 断开连接
    const disconnect = async () => {
      try {
        // 调用后端登出API
        if (authToken.value) {
          await fetch('/api/auth/logout', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${authToken.value}`
            }
          })
        }

        // 清除本地状态
        isConnected.value = false
        walletInfo.value = {}
        authToken.value = ''
        error.value = ''

        // 清除本地存储
        localStorage.removeItem('wallet_token')
        localStorage.removeItem('wallet_info')

        emit('disconnected')

      } catch (err) {
        console.error('断开连接失败:', err)
      }
    }

    // 复制钱包地址
    const copyAddress = async () => {
      try {
        await navigator.clipboard.writeText(walletInfo.value.public_key)
        // 可以添加一个临时提示
        console.log('地址已复制到剪贴板')
      } catch (err) {
        console.error('复制失败:', err)
      }
    }

    // 格式化地址显示
    const formatAddress = (address) => {
      if (!address) return ''
      return `${address.slice(0, 4)}...${address.slice(-4)}`
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
            walletInfo.value = JSON.parse(storedInfo)
            isConnected.value = true
            
            emit('connected', {
              token: storedToken,
              user: JSON.parse(storedInfo)
            })
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
      checkStoredAuth()
    })

    return {
      isConnected,
      connecting,
      walletInfo,
      error,
      connectPhantom,
      connectSolflare,
      disconnect,
      copyAddress,
      formatAddress
    }
  }
}
</script>

<style scoped>
.wallet-connect {
  max-width: 400px;
  margin: 0 auto;
  padding: 2rem;
}

.connect-section {
  text-align: center;
}

.wallet-header h2 {
  color: #333;
  margin-bottom: 0.5rem;
}

.wallet-header p {
  color: #666;
  margin-bottom: 2rem;
}

.wallet-options {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1rem;
}

.wallet-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  background: white;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 1rem;
  font-weight: 500;
}

.wallet-btn:hover:not(:disabled) {
  border-color: #007bff;
  background: #f8f9ff;
}

.wallet-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.wallet-icon {
  width: 24px;
  height: 24px;
  font-size: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.phantom-btn:hover:not(:disabled) {
  border-color: #ab9ff2;
  background: #f5f3ff;
}

.solflare-btn:hover:not(:disabled) {
  border-color: #ff6b35;
  background: #fff5f2;
}

.error-message {
  color: #dc3545;
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 8px;
  padding: 0.75rem;
  margin-top: 1rem;
}

.connected-section {
  text-align: center;
}

.wallet-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem;
  background: #f8f9fa;
  border-radius: 12px;
  margin-bottom: 1.5rem;
}

.wallet-avatar {
  flex-shrink: 0;
}

.avatar-circle {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.5rem;
  font-weight: bold;
}

.wallet-details {
  flex: 1;
  text-align: left;
}

.wallet-details h3 {
  margin: 0 0 0.25rem 0;
  color: #333;
}

.wallet-address {
  margin: 0 0 0.5rem 0;
  color: #666;
  font-family: monospace;
  font-size: 0.9rem;
}

.status-badge {
  background: #d4edda;
  color: #155724;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 500;
}

.wallet-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.btn-secondary {
  padding: 0.75rem 1.5rem;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.3s ease;
}

.btn-secondary:hover {
  background: #5a6268;
}

.btn-danger {
  padding: 0.75rem 1.5rem;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.3s ease;
}

.btn-danger:hover {
  background: #c82333;
}
</style>