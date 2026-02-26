/**
 * equipment.js - 装备推荐页面逻辑
 */

const EquipmentPage = {
  /**
   * 当前筛选条件
   */
  filters: {
    query: '',
    categories: [],
    brand: '',
    minPrice: null,
    maxPrice: null,
  },

  /**
   * 排序方式
   */
  sort: 'relevance',

  /**
   * 分页
   */
  page: 1,
  pageSize: 12,
  total: 0,

  /**
   * 对比列表
   */
  compareList: [],

  /**
   * 搜索防抖定时器
   */
  searchTimer: null,

  /**
   * 初始化
   */
  async init() {
    await this.loadBrands();
    await this.loadEquipments();

    // 恢复对比列表
    this.compareList = Storage.get('equipment_compare', []);
    this.updateCompareBar();
  },

  /**
   * 加载品牌列表
   */
  async loadBrands() {
    try {
      const brands = await equipmentApi.getBrands();
      const select = document.getElementById('brandFilter');
      if (select && brands) {
        brands.forEach(brand => {
          const option = document.createElement('option');
          option.value = brand.id || brand.name;
          option.textContent = brand.name;
          select.appendChild(option);
        });
      }
    } catch (e) {
      console.error('Failed to load brands:', e);
    }
  },

  /**
   * 加载装备列表
   */
  async loadEquipments() {
    const grid = document.getElementById('equipmentGrid');
    if (!grid) return;

    // 显示加载状态
    grid.innerHTML = Loading.skeleton('card', 6);

    try {
      const result = await equipmentApi.search({
        query: this.filters.query,
        category: this.filters.categories.join(','),
        brand: this.filters.brand,
        min_price: this.filters.minPrice,
        max_price: this.filters.maxPrice,
        sort: this.sort,
      }, (this.page - 1) * this.pageSize, this.pageSize);

      this.total = result.total || 0;
      this.renderEquipments(result.items || []);
      this.renderPagination();

      document.getElementById('resultCount').textContent = `共 ${this.total} 件装备`;
    } catch (e) {
      console.error('Failed to load equipments:', e);
      grid.innerHTML = `
        <div class="col-span-full empty-state">
          <div class="empty-state-title">加载失败</div>
          <button class="btn btn-primary mt-md" onclick="EquipmentPage.loadEquipments()">重试</button>
        </div>
      `;
    }
  },

  /**
   * 渲染装备列表
   * @param {Array} equipments - 装备列表
   */
  renderEquipments(equipments) {
    const grid = document.getElementById('equipmentGrid');
    if (!grid) return;

    if (equipments.length === 0) {
      grid.innerHTML = `
        <div class="col-span-full empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <div class="empty-state-title">未找到装备</div>
          <div class="empty-state-desc">尝试调整筛选条件</div>
        </div>
      `;
      return;
    }

    grid.innerHTML = equipments.map(item => this.renderEquipmentCard(item)).join('');
  },

  /**
   * 渲染装备卡片
   * @param {Object} item - 装备数据
   * @returns {string} HTML 字符串
   */
  renderEquipmentCard(item) {
    const isInCompare = this.compareList.some(c => c.id === item.id);
    const categoryLabels = {
      blade: '底板',
      rubber: '胶皮',
      ball: '球',
      accessory: '配件',
    };

    return `
      <div class="card equipment-card card-clickable" onclick="EquipmentPage.showDetail('${item.id}')">
        <div class="equipment-card-image">
          ${item.image ? `<img src="${item.image}" alt="${item.name}">` : `
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" style="color: var(--text-tertiary);">
              <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/>
            </svg>
          `}
        </div>
        <div class="equipment-card-body">
          <div class="equipment-card-brand">${item.brand || '未知品牌'}</div>
          <div class="equipment-card-name truncate">${item.name}</div>
          <div class="equipment-card-specs">
            <span class="tag">${categoryLabels[item.category] || item.category}</span>
            ${item.rating ? `<span class="tag">${Format.rating(item.rating)}</span>` : ''}
          </div>
          <div class="flex items-center justify-between mt-sm">
            <div class="equipment-card-price">${Format.price(item.price)}</div>
            <button class="btn btn-ghost btn-sm ${isInCompare ? 'text-primary' : ''}"
                    onclick="event.stopPropagation(); EquipmentPage.toggleCompare('${item.id}', '${item.name}')">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="${isInCompare ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
                <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    `;
  },

  /**
   * 渲染分页
   */
  renderPagination() {
    const container = document.getElementById('pagination');
    if (!container) return;

    Pagination.create(container, {
      page: this.page,
      pageSize: this.pageSize,
      total: this.total,
      onChange: (page) => {
        this.page = page;
        this.loadEquipments();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      },
    });
  },

  /**
   * 处理搜索
   */
  handleSearch() {
    clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => {
      this.filters.query = document.getElementById('searchInput').value.trim();
      this.page = 1;
      this.loadEquipments();
    }, 300);
  },

  /**
   * 处理筛选变化
   */
  handleFilterChange() {
    // 获取分类
    const categoryInputs = document.querySelectorAll('#categoryFilters input:checked');
    this.filters.categories = Array.from(categoryInputs).map(input => input.value);

    // 获取品牌
    this.filters.brand = document.getElementById('brandFilter').value;

    // 获取价格范围
    const minPrice = document.getElementById('minPrice').value;
    const maxPrice = document.getElementById('maxPrice').value;
    this.filters.minPrice = minPrice ? parseInt(minPrice) : null;
    this.filters.maxPrice = maxPrice ? parseInt(maxPrice) : null;

    this.page = 1;
    this.loadEquipments();
  },

  /**
   * 处理排序变化
   */
  handleSortChange() {
    this.sort = document.getElementById('sortSelect').value;
    this.page = 1;
    this.loadEquipments();
  },

  /**
   * 清除筛选
   */
  clearFilters() {
    // 重置表单
    document.getElementById('searchInput').value = '';
    document.querySelectorAll('#categoryFilters input').forEach(input => input.checked = false);
    document.getElementById('brandFilter').value = '';
    document.getElementById('minPrice').value = '';
    document.getElementById('maxPrice').value = '';

    // 重置状态
    this.filters = {
      query: '',
      categories: [],
      brand: '',
      minPrice: null,
      maxPrice: null,
    };
    this.page = 1;
    this.loadEquipments();
  },

  /**
   * 显示装备详情
   * @param {string} id - 装备 ID
   */
  async showDetail(id) {
    try {
      Loading.show('加载装备详情...');
      const equipment = await equipmentApi.getEquipment(id);
      Loading.hide();

      const content = `
        <div class="flex gap-lg">
          <div style="width: 200px; flex-shrink: 0;">
            <div style="background: var(--bg-light); border-radius: var(--radius); padding: 20px; text-align: center;">
              ${equipment.image ? `<img src="${equipment.image}" alt="${equipment.name}" style="max-width: 100%;">` : `
                <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" style="color: var(--text-tertiary);">
                  <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/>
                </svg>
              `}
            </div>
          </div>
          <div class="flex-1">
            <div class="text-sm text-secondary mb-xs">${equipment.brand || '未知品牌'}</div>
            <h2 style="font-size: 20px; margin-bottom: 8px;">${equipment.name}</h2>
            <div class="text-2xl font-bold text-primary mb-md">${Format.price(equipment.price)}</div>

            <div class="mb-md">
              ${equipment.rating ? `<div class="mb-sm">${Format.rating(equipment.rating)} (${equipment.review_count || 0} 条评价)</div>` : ''}
            </div>

            <div class="text-sm text-secondary mb-lg">${equipment.description || '暂无描述'}</div>

            ${equipment.specs ? `
              <div class="mb-lg">
                <h4 class="font-medium mb-sm">规格参数</h4>
                <div class="grid grid-cols-2 gap-sm">
                  ${Object.entries(equipment.specs).map(([key, value]) => `
                    <div class="text-sm">
                      <span class="text-secondary">${key}:</span>
                      <span class="font-medium">${value}</span>
                    </div>
                  `).join('')}
                </div>
              </div>
            ` : ''}

            <div class="flex gap-sm">
              <button class="btn btn-primary" onclick="EquipmentPage.toggleCompare('${equipment.id}', '${equipment.name}'); Modal.close();">
                添加到对比
              </button>
              <button class="btn btn-secondary" onclick="Modal.close();">关闭</button>
            </div>
          </div>
        </div>
      `;

      Modal.open({
        title: '装备详情',
        content,
        size: 'lg',
      });
    } catch (e) {
      Loading.hide();
      Toast.error('加载失败');
    }
  },

  /**
   * 切换对比
   * @param {string} id - 装备 ID
   * @param {string} name - 装备名称
   */
  toggleCompare(id, name) {
    const index = this.compareList.findIndex(c => c.id === id);

    if (index >= 0) {
      this.compareList.splice(index, 1);
    } else {
      if (this.compareList.length >= 4) {
        Toast.warning('最多可对比 4 件装备');
        return;
      }
      this.compareList.push({ id, name });
    }

    Storage.set('equipment_compare', this.compareList);
    this.updateCompareBar();
    this.loadEquipments(); // 刷新列表以更新对比按钮状态
  },

  /**
   * 更新对比栏
   */
  updateCompareBar() {
    const bar = document.getElementById('compareBar');
    const items = document.getElementById('compareItems');
    const count = document.getElementById('compareCount');

    if (!bar || !items) return;

    if (this.compareList.length > 0) {
      bar.classList.add('visible');
      count.textContent = this.compareList.length;
      items.innerHTML = this.compareList.map(item => `
        <div class="compare-item">
          <span class="truncate" style="max-width: 100px;">${item.name}</span>
          <button onclick="EquipmentPage.toggleCompare('${item.id}', '${item.name}')" style="padding: 2px;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      `).join('');
    } else {
      bar.classList.remove('visible');
    }
  },

  /**
   * 清空对比
   */
  clearCompare() {
    this.compareList = [];
    Storage.remove('equipment_compare');
    this.updateCompareBar();
    this.loadEquipments();
  },

  /**
   * 显示对比弹窗
   */
  async showCompareModal() {
    if (this.compareList.length < 2) {
      Toast.warning('请至少选择 2 件装备进行对比');
      return;
    }

    try {
      Loading.show('加载对比数据...');
      const result = await equipmentApi.compare(this.compareList.map(c => c.id));
      Loading.hide();

      const equipments = result.equipments || [];
      const specs = result.specs || [];

      const content = `
        <div style="overflow-x: auto;">
          <table style="min-width: 600px;">
            <thead>
              <tr>
                <th style="width: 120px;"></th>
                ${equipments.map(eq => `<th style="text-align: center;">${eq.name}</th>`).join('')}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="font-medium">品牌</td>
                ${equipments.map(eq => `<td style="text-align: center;">${eq.brand || '-'}</td>`).join('')}
              </tr>
              <tr>
                <td class="font-medium">价格</td>
                ${equipments.map(eq => `<td style="text-align: center;">${Format.price(eq.price)}</td>`).join('')}
              </tr>
              <tr>
                <td class="font-medium">评分</td>
                ${equipments.map(eq => `<td style="text-align: center;">${eq.rating ? Format.rating(eq.rating) : '-'}</td>`).join('')}
              </tr>
              ${specs.map(spec => `
                <tr>
                  <td class="font-medium">${spec.name}</td>
                  ${equipments.map(eq => `<td style="text-align: center;">${eq.specs?.[spec.key] || '-'}</td>`).join('')}
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;

      Modal.open({
        title: '装备对比',
        content,
        size: 'xl',
      });
    } catch (e) {
      Loading.hide();
      Toast.error('加载对比数据失败');
    }
  },

  /**
   * 显示推荐弹窗
   */
  showRecommendModal() {
    const content = `
      <form id="recommendForm" onsubmit="EquipmentPage.getRecommendations(event)">
        <div class="form-group">
          <label class="form-label">您的水平</label>
          <select id="level" class="form-input form-select" required>
            <option value="">请选择</option>
            <option value="beginner">初学者</option>
            <option value="intermediate">业余爱好者</option>
            <option value="advanced">进阶选手</option>
            <option value="professional">专业选手</option>
          </select>
        </div>

        <div class="form-group">
          <label class="form-label">打法风格</label>
          <select id="playStyle" class="form-input form-select" required>
            <option value="">请选择</option>
            <option value="offensive">进攻型</option>
            <option value="defensive">防守型</option>
            <option value="allround">全面型</option>
            <option value="control">控制型</option>
          </select>
        </div>

        <div class="form-group">
          <label class="form-label">预算范围 (元)</label>
          <div class="flex gap-sm items-center">
            <input type="number" id="budgetMin" class="form-input" placeholder="最低" style="width: 120px;">
            <span>-</span>
            <input type="number" id="budgetMax" class="form-input" placeholder="最高" style="width: 120px;">
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">偏好 (可多选)</label>
          <div class="checkbox-group">
            <label class="checkbox-label"><input type="checkbox" name="pref" value="speed"> 速度</label>
            <label class="checkbox-label"><input type="checkbox" name="pref" value="spin"> 旋转</label>
            <label class="checkbox-label"><input type="checkbox" name="pref" value="control"> 控制</label>
            <label class="checkbox-label"><input type="checkbox" name="pref" value="durability"> 耐用</label>
          </div>
        </div>

        <button type="submit" class="btn btn-primary btn-block">获取推荐</button>
      </form>
    `;

    Modal.open({
      title: '获取个性化推荐',
      content,
      size: 'sm',
    });
  },

  /**
   * 获取推荐
   * @param {Event} event - 表单提交事件
   */
  async getRecommendations(event) {
    event.preventDefault();

    const level = document.getElementById('level').value;
    const playStyle = document.getElementById('playStyle').value;
    const budgetMin = document.getElementById('budgetMin').value;
    const budgetMax = document.getElementById('budgetMax').value;
    const prefs = Array.from(document.querySelectorAll('input[name="pref"]:checked')).map(c => c.value);

    Modal.close();
    Loading.show('正在生成推荐...');

    try {
      const recommendations = await equipmentApi.getRecommendations({
        level,
        play_style: playStyle,
        budget_min: budgetMin ? parseInt(budgetMin) : null,
        budget_max: budgetMax ? parseInt(budgetMax) : null,
        preferences: prefs,
      });

      Loading.hide();

      if (!recommendations || recommendations.length === 0) {
        Toast.info('暂无匹配的推荐');
        return;
      }

      const content = `
        <div class="list">
          ${recommendations.map((item, index) => `
            <div class="list-item" style="cursor: pointer;" onclick="EquipmentPage.showDetail('${item.id}')">
              <div class="avatar" style="background-color: var(--primary-bg); color: var(--primary);">
                ${index + 1}
              </div>
              <div class="list-item-content">
                <div class="list-item-title">${item.name}</div>
                <div class="list-item-desc">${item.brand} · ${Format.price(item.price)}</div>
              </div>
              <div class="badge badge-success">${item.match_score || 90}% 匹配</div>
            </div>
          `).join('')}
        </div>
      `;

      Modal.open({
        title: '推荐结果',
        content,
        size: 'md',
      });
    } catch (e) {
      Loading.hide();
      Toast.error('获取推荐失败');
    }
  },
};

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
  EquipmentPage.init();
});

window.EquipmentPage = EquipmentPage;
