/**
 * 执行报告相关API
 */

import { request } from '@/utils/http'

const API_PREFIX = '/api/v1/execution-reports'

/**
 * 获取执行报告列表
 * @param {Object} params 查询参数
 * @returns {Promise}
 */
export function getExecutionReports(params = {}) {
  return request({
    url: API_PREFIX,
    method: 'GET',
    params
  })
}

/**
 * 获取执行报告详情
 * @param {string} executionId 执行ID
 * @returns {Promise}
 */
export function getExecutionReportDetail(executionId) {
  return request({
    url: `${API_PREFIX}/${executionId}`,
    method: 'GET'
  })
}

/**
 * 获取执行统计信息
 * @param {Object} params 查询参数
 * @returns {Promise}
 */
export function getExecutionStatistics(params = {}) {
  return request({
    url: `${API_PREFIX}/statistics/summary`,
    method: 'GET',
    params
  })
}

/**
 * 生成执行报告
 * @param {string} executionId 执行ID
 * @param {Object} data 生成参数
 * @returns {Promise}
 */
export function generateExecutionReport(executionId, data) {
  return request({
    url: `${API_PREFIX}/${executionId}/generate`,
    method: 'POST',
    data
  })
}

/**
 * 预览报告文件
 * @param {string} executionId 执行ID
 * @param {string} fileName 文件名
 * @returns {Promise}
 */
export function previewReportFile(executionId, fileName) {
  return request({
    url: `${API_PREFIX}/${executionId}/preview/${fileName}`,
    method: 'GET',
    responseType: 'text'
  })
}

/**
 * 下载报告文件
 * @param {string} executionId 执行ID
 * @param {string} fileName 文件名
 * @returns {string} 下载链接
 */
export function getReportDownloadUrl(executionId, fileName) {
  return `${API_PREFIX}/${executionId}/download/${fileName}`
}

/**
 * 获取执行日志
 * @param {string} executionId 执行ID
 * @param {Object} params 查询参数
 * @returns {Promise}
 */
export function getExecutionLogs(executionId, params = {}) {
  return request({
    url: `${API_PREFIX}/${executionId}/logs`,
    method: 'GET',
    params
  })
}

/**
 * 删除执行报告
 * @param {string} executionId 执行ID
 * @returns {Promise}
 */
export function deleteExecutionReport(executionId) {
  return request({
    url: `${API_PREFIX}/${executionId}`,
    method: 'DELETE'
  })
}

/**
 * 导出执行报告
 * @param {string} executionId 执行ID
 * @param {string} format 导出格式
 * @returns {Promise}
 */
export function exportExecutionReport(executionId, format = 'json') {
  return request({
    url: `${API_PREFIX}/${executionId}/export`,
    method: 'GET',
    params: { format }
  })
}

/**
 * 分享执行报告
 * @param {string} executionId 执行ID
 * @returns {Promise}
 */
export function shareExecutionReport(executionId) {
  return request({
    url: `${API_PREFIX}/${executionId}/share`,
    method: 'POST'
  })
}

/**
 * 获取分享的报告
 * @param {string} shareToken 分享token
 * @returns {Promise}
 */
export function getSharedReport(shareToken) {
  return request({
    url: `${API_PREFIX}/shared/${shareToken}`,
    method: 'GET'
  })
}

/**
 * 批量删除执行报告
 * @param {Array} executionIds 执行ID列表
 * @returns {Promise}
 */
export function batchDeleteExecutionReports(executionIds) {
  const promises = executionIds.map(id => deleteExecutionReport(id))
  return Promise.all(promises)
}

/**
 * 获取报告文件内容
 * @param {string} executionId 执行ID
 * @param {string} fileName 文件名
 * @returns {Promise}
 */
export function getReportContent(executionId, fileName) {
  return request({
    url: `${API_PREFIX}/${executionId}/preview/${fileName}`,
    method: 'GET'
  })
}

/**
 * 获取执行报告趋势数据
 * @param {Object} params 查询参数
 * @returns {Promise}
 */
export function getExecutionTrends(params = {}) {
  return request({
    url: `${API_PREFIX}/trends`,
    method: 'GET',
    params
  })
}

/**
 * 获取执行报告对比数据
 * @param {Array} executionIds 执行ID列表
 * @returns {Promise}
 */
export function compareExecutionReports(executionIds) {
  return request({
    url: `${API_PREFIX}/compare`,
    method: 'POST',
    data: { execution_ids: executionIds }
  })
}

/**
 * 获取执行报告模板
 * @returns {Promise}
 */
export function getReportTemplates() {
  return request({
    url: `${API_PREFIX}/templates`,
    method: 'GET'
  })
}

/**
 * 创建自定义报告模板
 * @param {Object} template 模板数据
 * @returns {Promise}
 */
export function createReportTemplate(template) {
  return request({
    url: `${API_PREFIX}/templates`,
    method: 'POST',
    data: template
  })
}

/**
 * 使用模板生成报告
 * @param {string} executionId 执行ID
 * @param {string} templateId 模板ID
 * @returns {Promise}
 */
export function generateReportWithTemplate(executionId, templateId) {
  return request({
    url: `${API_PREFIX}/${executionId}/generate-with-template`,
    method: 'POST',
    data: { template_id: templateId }
  })
}

/**
 * 获取执行报告摘要
 * @param {Array} executionIds 执行ID列表
 * @returns {Promise}
 */
export function getExecutionReportsSummary(executionIds) {
  return request({
    url: `${API_PREFIX}/summary`,
    method: 'POST',
    data: { execution_ids: executionIds }
  })
}

/**
 * 搜索执行报告
 * @param {Object} searchParams 搜索参数
 * @returns {Promise}
 */
export function searchExecutionReports(searchParams) {
  return request({
    url: `${API_PREFIX}/search`,
    method: 'POST',
    data: searchParams
  })
}

/**
 * 获取执行报告标签
 * @returns {Promise}
 */
export function getExecutionReportTags() {
  return request({
    url: `${API_PREFIX}/tags`,
    method: 'GET'
  })
}

/**
 * 为执行报告添加标签
 * @param {string} executionId 执行ID
 * @param {Array} tags 标签列表
 * @returns {Promise}
 */
export function addExecutionReportTags(executionId, tags) {
  return request({
    url: `${API_PREFIX}/${executionId}/tags`,
    method: 'POST',
    data: { tags }
  })
}

/**
 * 获取执行报告评论
 * @param {string} executionId 执行ID
 * @returns {Promise}
 */
export function getExecutionReportComments(executionId) {
  return request({
    url: `${API_PREFIX}/${executionId}/comments`,
    method: 'GET'
  })
}

/**
 * 添加执行报告评论
 * @param {string} executionId 执行ID
 * @param {string} comment 评论内容
 * @returns {Promise}
 */
export function addExecutionReportComment(executionId, comment) {
  return request({
    url: `${API_PREFIX}/${executionId}/comments`,
    method: 'POST',
    data: { comment }
  })
}

export default {
  getExecutionReports,
  getExecutionReportDetail,
  getExecutionStatistics,
  generateExecutionReport,
  previewReportFile,
  getReportDownloadUrl,
  getExecutionLogs,
  deleteExecutionReport,
  exportExecutionReport,
  shareExecutionReport,
  getSharedReport,
  batchDeleteExecutionReports,
  getReportContent,
  getExecutionTrends,
  compareExecutionReports,
  getReportTemplates,
  createReportTemplate,
  generateReportWithTemplate,
  getExecutionReportsSummary,
  searchExecutionReports,
  getExecutionReportTags,
  addExecutionReportTags,
  getExecutionReportComments,
  addExecutionReportComment
}
