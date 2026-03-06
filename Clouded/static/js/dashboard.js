let currentUser = null;

async function loadDashboard() {
  try {
    const response = await auth.apiRequest('/protected');
    
    if (!response || !response.ok) {
      window.location.href = '/login.html';
      return;
    }

    const data = await response.json();
    currentUser = data.username;

    document.getElementById('username').textContent = data.username;
    document.getElementById('userAvatar').textContent = 
      data.username[0].toUpperCase();

    loadDeployments();
  } catch (error) {
    console.error('Failed to load dashboard:', error);
    window.location.href = '/login.html';
  }
}

function loadDeployments() {
  const deploymentsGrid = document.getElementById('deploymentsGrid');
  
  const mockDeployments = [
    {
      name: 'my-awesome-app',
      url: 'my-awesome-app.clouded.tn3w.dev',
      status: 'active',
      repo: 'github.com/user/my-awesome-app',
      lastDeploy: '2 hours ago'
    },
    {
      name: 'portfolio-site',
      url: 'portfolio.clouded.tn3w.dev',
      status: 'building',
      repo: 'github.com/user/portfolio-site',
      lastDeploy: '5 minutes ago'
    },
    {
      name: 'api-service',
      url: 'api.clouded.tn3w.dev',
      status: 'active',
      repo: 'github.com/user/api-service',
      lastDeploy: '1 day ago'
    }
  ];

  deploymentsGrid.innerHTML = mockDeployments.map(deployment => `
    <div class="deployment-card">
      <div class="deployment-header">
        <div>
          <div class="deployment-title">${deployment.name}</div>
          <div class="deployment-url">${deployment.url}</div>
        </div>
        <span class="status-badge status-${deployment.status}">
          ${deployment.status}
        </span>
      </div>
      <div style="margin-top: 1rem; padding-top: 1rem; 
                  border-top: 1px solid var(--border);">
        <div style="font-size: 0.85rem; color: var(--text-secondary); 
                    margin-bottom: 0.5rem;">
          📦 ${deployment.repo}
        </div>
        <div style="font-size: 0.85rem; color: var(--text-secondary);">
          🕐 Last deploy: ${deployment.lastDeploy}
        </div>
      </div>
      <div style="margin-top: 1rem; display: flex; gap: 0.5rem;">
        <button class="btn btn-secondary" 
                style="padding: 0.5rem 1rem; font-size: 0.85rem;">
          View Logs
        </button>
        <button class="btn btn-secondary" 
                style="padding: 0.5rem 1rem; font-size: 0.85rem;">
          Redeploy
        </button>
      </div>
    </div>
  `).join('');
}

function logout() {
  auth.clearTokens();
  window.location.href = '/login.html';
}

document.getElementById('logoutBtn').addEventListener('click', logout);
document.getElementById('newDeployBtn').addEventListener('click', () => {
  alert('New deployment feature coming soon!');
});

loadDashboard();
