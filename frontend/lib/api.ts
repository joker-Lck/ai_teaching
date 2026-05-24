/**
 * API 客户端 - 封装与后端的所有通信
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api';

interface RequestOptions {
  method?: string;
  body?: any;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('auth_token', token);
    } else {
      localStorage.removeItem('auth_token');
    }
  }

  getToken(): string | null {
    if (!this.token) {
      this.token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    }
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { method = 'GET', body, headers = {}, signal } = options;

    const token = this.getToken();
    const defaultHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    };

    const response = await fetch(`${API_BASE}${endpoint}`, {
      method,
      headers: defaultHeaders,
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });

    if (response.status === 401) {
      this.setToken(null);
      if (typeof window !== 'undefined') {
        window.location.href = '/';
      }
      throw new Error('认证已过期，请重新登录');
    }

    const data = await response.json();
    return data as T;
  }

  // ==================== 认证 API ====================

  async login(username: string, password: string) {
    return this.request('/auth/login', {
      method: 'POST',
      body: { username, password },
    });
  }

  async register(username: string, password: string, email?: string, role?: string) {
    return this.request('/auth/register', {
      method: 'POST',
      body: { username, password, email, role },
    });
  }

  async guestLogin() {
    return this.request('/auth/guest', { method: 'POST' });
  }

  async getMe() {
    return this.request('/auth/me');
  }

  // ==================== 智能答疑 API ====================

  async askQuestion(question: string, scenario: string, signal?: AbortSignal) {
    return this.request('/qa/ask-sync', {
      method: 'POST',
      body: { question, scenario },
      signal,
    });
  }

  async getQAHistory(limit = 50) {
    return this.request(`/qa/history?limit=${limit}`);
  }

  async clearQAHistory() {
    return this.request('/qa/history', { method: 'DELETE' });
  }

  async searchKnowledge(query: string) {
    return this.request('/qa/search', {
      method: 'POST',
      body: { question: query },
    });
  }

  // ==================== 课件生成 API ====================

  async generateCourseware(topic: string, requirements: string, fastMode: boolean) {
    return this.request('/courseware/generate', {
      method: 'POST',
      body: { topic, requirements, fast_mode: fastMode },
    });
  }

  async identifySubject(topic: string, requirements: string) {
    return this.request('/courseware/identify', {
      method: 'POST',
      body: { topic, requirements },
    });
  }

  async clarifyRequirements(topic: string, history: any[]) {
    return this.request('/courseware/clarify', {
      method: 'POST',
      body: { topic, conversation_history: history },
    });
  }

  async clarifyReply(topic: string, history: any[]) {
    return this.request('/courseware/clarify-reply', {
      method: 'POST',
      body: { topic, conversation_history: history },
    });
  }

  async refineCourseware(feedback: string, topic: string, subject: string, slides: any[]) {
    return this.request('/courseware/refine', {
      method: 'POST',
      body: { feedback, topic, subject, slides },
    });
  }

  async getCoursewareHistory() {
    return this.request('/courseware/history');
  }

  async getCoursewareDetail(id: number) {
    return this.request(`/courseware/history/${id}`);
  }

  getCoursewareDownloadUrl(id: number, format: string = 'pptx') {
    return `${API_BASE}/courseware/download/${id}?format=${format}`;
  }

  // ==================== 知识库 API ====================

  async getKnowledgeStats() {
    return this.request('/knowledge/stats');
  }

  async getKnowledgeDocuments(limit = 100, subject?: string) {
    const params = new URLSearchParams({ limit: String(limit) });
    if (subject) params.append('subject', subject);
    return this.request(`/knowledge/documents?${params}`);
  }

  async deleteKnowledgeDocument(id: number) {
    return this.request(`/knowledge/documents/${id}`, { method: 'DELETE' });
  }

  async clearKnowledgeDocuments() {
    return this.request('/knowledge/documents', { method: 'DELETE' });
  }

  async searchKnowledgeDocuments(query: string, subject?: string, limit = 10) {
    return this.request('/knowledge/search', {
      method: 'POST',
      body: { query, subject, limit },
    });
  }

  async analyzeKnowledgeDocuments() {
    return this.request('/knowledge/analyze', { method: 'POST' });
  }

  // ==================== 学情分析 API ====================

  async generateAnalysisReport(mode: string, studentName?: string, className?: string, totalStudents?: number) {
    return this.request('/analysis/report', {
      method: 'POST',
      body: {
        analysis_mode: mode,
        student_name: studentName,
        class_name: className,
        total_students: totalStudents,
      },
    });
  }

  async getAnalysisData() {
    return this.request('/analysis/data');
  }

  async manageAnalysisData(action: string, keyword?: string, format?: string) {
    return this.request('/analysis/data-manage', {
      method: 'POST',
      body: { action, keyword, format },
    });
  }

  // ==================== SSE 流式请求 ====================

  async streamRequest(
    endpoint: string,
    body: any,
    onChunk: (chunk: string) => void,
    onDone: (data: any) => void,
    onError: (error: string) => void,
  ) {
    const token = this.getToken();
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      onError(`HTTP ${response.status}`);
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
      onError('无法读取响应流');
      return;
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.type === 'chunk') {
                onChunk(data.content);
              } else if (data.type === 'done') {
                onDone(data);
              } else if (data.type === 'error') {
                onError(data.message);
              } else if (data.type === 'status') {
                // 状态消息，可用于显示进度
              }
            } catch {
              // 非 JSON 数据，忽略
            }
          }
        }
      }
    } catch (error: any) {
      if (error.name !== 'AbortError') {
        onError(error.message);
      }
    }
  }

  // 流式问答
  async askQuestionStream(
    question: string,
    scenario: string,
    onChunk: (chunk: string) => void,
    onDone: (data: any) => void,
    onError: (error: string) => void,
  ) {
    return this.streamRequest('/qa/ask', { question, scenario }, onChunk, onDone, onError);
  }

  // 流式生成课件
  async generateCoursewareStream(
    topic: string,
    requirements: string,
    fastMode: boolean,
    onChunk: (chunk: string) => void,
    onDone: (data: any) => void,
    onError: (error: string) => void,
  ) {
    return this.streamRequest(
      '/courseware/generate-stream',
      { topic, requirements, fast_mode: fastMode },
      onChunk,
      onDone,
      onError,
    );
  }
}

// 单例导出
export const api = new ApiClient();
export default api;
