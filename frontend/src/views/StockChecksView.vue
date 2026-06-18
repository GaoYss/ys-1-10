<template>
  <section>
    <template v-if="!editingCheck && !viewingCheck">
      <PageHeader eyebrow="Stock Check" title="门店盘点">
        <button class="primary-btn" @click="startNewCheck">新建盘点单</button>
      </PageHeader>

      <div class="toolbar">
        <label class="checkbox-line">
          <input v-model="onlyDraft" type="checkbox" @change="loadChecks" />
          只看草稿
        </label>
      </div>

      <DataTable :columns="listColumns" :rows="checks">
        <template #status="{ row }">
          <StatusBadge
            :label="row.status === 'draft' ? '草稿' : '已完成'"
            :variant="row.status === 'draft' ? 'neutral' : 'success'"
          />
        </template>
        <template #summary="{ row }">
          <span>
            <span v-if="row.profitCount > 0" class="badge success">
              盘盈 {{ row.profitCount }}
            </span>
            <span v-if="row.lossCount > 0" class="badge danger" style="margin-left: 6px;">
              盘亏 {{ row.lossCount }}
            </span>
            <span v-if="row.profitCount === 0 && row.lossCount === 0" class="badge neutral">
              无差异
            </span>
          </span>
        </template>
        <template #createdAt="{ row }">{{ formatDateTime(row.createdAt) }}</template>
        <template #completedAt="{ row }">{{ formatDateTime(row.completedAt) }}</template>
        <template #actions="{ row }">
          <button class="secondary-btn" style="margin-right: 6px;" @click="viewCheck(row.id)">
            查看
          </button>
          <button
            v-if="row.status === 'draft'"
            class="secondary-btn"
            style="margin-right: 6px;"
            @click="editCheck(row.id)"
          >
            编辑
          </button>
          <button
            v-if="row.status === 'draft'"
            class="secondary-btn"
            style="background: #ffe4e2; color: #a72f25;"
            @click="deleteCheck(row.id)"
          >
            删除
          </button>
        </template>
      </DataTable>
    </template>

    <template v-else>
      <PageHeader
        :eyebrow="editingCheck ? (editingCheck.id ? 'Edit Check' : 'New Check') : 'Check Detail'"
        :title="editingCheck ? (editingCheck.id ? '编辑盘点单' : '新建盘点单') : '盘点单详情'"
      >
        <button class="secondary-btn" @click="backToList">返回列表</button>
      </PageHeader>

      <section v-if="editingCheck" class="form-panel">
        <div class="form-grid">
          <label>
            经办人
            <input v-model="editingCheck.operator" />
          </label>
          <label class="span-2">
            备注
            <input v-model="editingCheck.note" placeholder="可选" />
          </label>
        </div>
      </section>

      <section v-if="viewingCheck" class="form-panel">
        <div class="form-grid">
          <label>
            盘点单号
            <input :value="viewingCheck.checkNo" disabled />
          </label>
          <label>
            状态
            <input :value="viewingCheck.status === 'draft' ? '草稿' : '已完成'" disabled />
          </label>
          <label>
            经办人
            <input :value="viewingCheck.operator" disabled />
          </label>
          <label>
            创建时间
            <input :value="formatDateTime(viewingCheck.createdAt)" disabled />
          </label>
          <label>
            完成时间
            <input :value="formatDateTime(viewingCheck.completedAt)" disabled />
          </label>
          <label class="span-2">
            备注
            <input :value="viewingCheck.note || '-'" disabled />
          </label>
        </div>
      </section>

      <div v-if="editingCheck && !editingCheck.id" class="toolbar">
        <button class="primary-btn" @click="addAllIngredients">添加全部原料</button>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>原料</th>
              <th>分类</th>
              <th>系统库存</th>
              <th>实盘数量</th>
              <th>差异数量</th>
              <th>差异类型</th>
              <th v-if="editingCheck">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!currentItems.length">
              <td :colspan="editingCheck ? 7 : 6" class="empty-cell">暂无数据</td>
            </tr>
            <tr v-for="(item, idx) in currentItems" :key="item.ingredientId || idx">
              <td>{{ item.ingredientName }}</td>
              <td>{{ item.category }}</td>
              <td>{{ item.systemStock }} {{ item.unit }}</td>
              <td>
                <input
                  v-if="editingCheck"
                  v-model.number="item.actualStock"
                  type="number"
                  min="0"
                  step="0.01"
                  style="max-width: 140px;"
                  @input="recalcDiff(item)"
                />
                <span v-else>{{ item.actualStock }} {{ item.unit }}</span>
              </td>
              <td :style="{ color: getDiffColor(item) }">
                {{ item.diffQuantity > 0 ? '+' : '' }}{{ item.diffQuantity }} {{ item.unit }}
              </td>
              <td>
                <StatusBadge
                  v-if="item.diffType === 'profit'"
                  label="盘盈"
                  variant="success"
                />
                <StatusBadge
                  v-else-if="item.diffType === 'loss'"
                  label="盘亏"
                  variant="danger"
                />
                <StatusBadge v-else label="一致" variant="neutral" />
              </td>
              <td v-if="editingCheck">
                <button
                  class="secondary-btn"
                  style="background: #ffe4e2; color: #a72f25;"
                  @click="removeItem(idx)"
                >
                  移除
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="editingCheck" class="line-editor" style="justify-content: flex-end; margin-top: 18px;">
        <button class="secondary-btn" @click="backToList">取消</button>
        <button class="primary-btn" @click="saveDraft" style="margin-left: 10px;">
          {{ editingCheck.id ? '保存草稿' : '创建草稿' }}
        </button>
        <button
          class="primary-btn"
          style="margin-left: 10px; background: #17713d;"
          @click="submitCheck"
        >
          提交盘点
        </button>
      </div>
    </template>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'

import { inventoryApi } from '../api/inventory'
import { stockChecksApi } from '../api/stockChecks'
import DataTable from '../components/DataTable.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { formatDateTime } from '../utils/format'

const checks = ref([])
const ingredients = ref([])
const onlyDraft = ref(false)
const editingCheck = ref(null)
const viewingCheck = ref(null)
const error = ref('')

const listColumns = [
  { key: 'checkNo', label: '盘点单号' },
  { key: 'operator', label: '经办人' },
  { key: 'status', label: '状态' },
  { key: 'summary', label: '差异统计' },
  { key: 'itemCount', label: '原料数' },
  { key: 'createdAt', label: '创建时间' },
  { key: 'completedAt', label: '完成时间' },
  { key: 'actions', label: '操作' }
]

const currentItems = ref([])

async function loadChecks() {
  const params = onlyDraft.value ? { status: 'draft' } : {}
  const res = await stockChecksApi.list(params)
  checks.value = res.data
}

async function loadIngredients() {
  const res = await inventoryApi.options()
  ingredients.value = res.data.ingredients
}

function startNewCheck() {
  editingCheck.value = reactive({
    id: null,
    operator: '系统管理员',
    note: ''
  })
  currentItems.value = []
  viewingCheck.value = null
}

function addAllIngredients() {
  const existingIds = new Set(currentItems.value.map((it) => it.ingredientId))
  for (const ing of ingredients.value) {
    if (!existingIds.has(ing.id)) {
      const item = {
        ingredientId: ing.id,
        ingredientName: ing.name,
        category: ing.category,
        unit: ing.unit,
        systemStock: ing.stock,
        actualStock: ing.stock,
        diffQuantity: 0,
        diffType: 'normal'
      }
      currentItems.value.push(item)
    }
  }
}

function recalcDiff(item) {
  const diff = Number(item.actualStock) - Number(item.systemStock)
  item.diffQuantity = Number(diff.toFixed(4))
  if (diff > 0) item.diffType = 'profit'
  else if (diff < 0) item.diffType = 'loss'
  else item.diffType = 'normal'
}

function removeItem(idx) {
  currentItems.value.splice(idx, 1)
}

function getDiffColor(item) {
  if (item.diffType === 'profit') return '#17713d'
  if (item.diffType === 'loss') return '#a72f25'
  return '#223029'
}

function backToList() {
  editingCheck.value = null
  viewingCheck.value = null
  currentItems.value = []
  loadChecks()
}

async function saveDraft() {
  if (!currentItems.value.length) {
    alert('请添加盘点原料')
    return
  }
  const payload = {
    operator: editingCheck.value.operator,
    note: editingCheck.value.note,
    items: currentItems.value.map((it) => ({
      ingredientId: it.ingredientId,
      actualStock: it.actualStock
    }))
  }
  if (editingCheck.value.id) {
    await stockChecksApi.update(editingCheck.value.id, payload)
  } else {
    const res = await stockChecksApi.create(payload)
    editingCheck.value.id = res.data.id
  }
  backToList()
}

async function submitCheck() {
  if (!currentItems.value.length) {
    alert('请添加盘点原料')
    return
  }
  if (!confirm('提交后将自动更新库存并生成出入库记录，是否确认提交？')) {
    return
  }
  try {
    let checkId = editingCheck.value.id
    const payload = {
      operator: editingCheck.value.operator,
      note: editingCheck.value.note,
      items: currentItems.value.map((it) => ({
        ingredientId: it.ingredientId,
        actualStock: it.actualStock
      }))
    }
    if (!checkId) {
      const res = await stockChecksApi.create(payload)
      checkId = res.data.id
    } else {
      await stockChecksApi.update(checkId, payload)
    }
    await stockChecksApi.submit(checkId)
    backToList()
  } catch (err) {
    error.value = err.response?.data?.message || '提交失败'
  }
}

async function editCheck(id) {
  const res = await stockChecksApi.get(id)
  const data = res.data
  editingCheck.value = reactive({
    id: data.id,
    operator: data.operator,
    note: data.note || ''
  })
  currentItems.value = data.items.map((it) => ({ ...it }))
  viewingCheck.value = null
}

async function viewCheck(id) {
  const res = await stockChecksApi.get(id)
  viewingCheck.value = res.data
  currentItems.value = res.data.items
  editingCheck.value = null
}

async function deleteCheck(id) {
  if (!confirm('确认删除该盘点草稿？')) return
  await stockChecksApi.remove(id)
  loadChecks()
}

onMounted(async () => {
  await Promise.all([loadChecks(), loadIngredients()])
})
</script>
