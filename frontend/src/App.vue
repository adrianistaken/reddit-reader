<script setup>
import { computed, ref } from 'vue'

const redditUrl = ref('')
const loading = ref(false)
const error = ref('')
const result = ref(null)
const copied = ref(false)

const canGenerate = computed(() => redditUrl.value.trim().length > 0 && !loading.value)

async function generateMarkdown() {
  error.value = ''
  copied.value = false
  result.value = null
  loading.value = true

  try {
    const response = await fetch('/api/recap', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ url: redditUrl.value.trim() }),
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(data.detail || 'Unable to generate markdown.')
    }
    result.value = data
  } catch (err) {
    error.value = err.message || 'Unable to generate markdown.'
  } finally {
    loading.value = false
  }
}

async function copyMarkdown() {
  if (!result.value?.markdown) return
  await navigator.clipboard.writeText(result.value.markdown)
  copied.value = true
  window.setTimeout(() => {
    copied.value = false
  }, 1600)
}

function safeFilename() {
  if (result.value?.filename) return result.value.filename
  const title = result.value?.title || 'reddit-recap'
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80)
  return `${slug || 'reddit-recap'}.md`
}

function downloadMarkdown() {
  if (!result.value?.markdown) return
  const blob = new Blob([result.value.markdown], { type: 'text/markdown;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = safeFilename()
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(link.href)
}
</script>

<template>
  <main class="page-shell">
    <section class="workspace">
      <header class="masthead">
        <div>
          <p class="eyebrow">Private utility</p>
          <h1>Reddit Match Thread Recap</h1>
          <p class="lede">Paste a Reddit thread URL and generate a markdown recap for content research.</p>
        </div>
      </header>

      <form class="generator" @submit.prevent="generateMarkdown">
        <label for="reddit-url">Reddit thread URL</label>
        <div class="input-row">
          <input
            id="reddit-url"
            v-model="redditUrl"
            type="url"
            placeholder="https://www.reddit.com/r/DotA2/comments/..."
            autocomplete="off"
          />
          <button type="submit" :disabled="!canGenerate">
            {{ loading ? 'Generating...' : 'Generate Markdown' }}
          </button>
        </div>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
      </form>

      <section v-if="result" class="result" aria-live="polite">
        <div class="result-header">
          <div>
            <p class="eyebrow">Generated recap</p>
            <h2>{{ result.title }}</h2>
          </div>
          <div class="actions">
            <button type="button" class="secondary" @click="copyMarkdown">
              {{ copied ? 'Copied' : 'Copy Markdown' }}
            </button>
            <button type="button" class="secondary" @click="downloadMarkdown">
              Download .md
            </button>
          </div>
        </div>

        <dl class="meta-grid">
          <div>
            <dt>Subreddit</dt>
            <dd>r/{{ result.subreddit }}</dd>
          </div>
          <div>
            <dt>Comments processed</dt>
            <dd>{{ result.comment_count }}</dd>
          </div>
          <div class="url-meta">
            <dt>Original URL</dt>
            <dd><a :href="result.url" target="_blank" rel="noreferrer">{{ result.url }}</a></dd>
          </div>
        </dl>

        <textarea
          class="markdown-preview"
          readonly
          :value="result.markdown"
          aria-label="Generated markdown preview"
        />
      </section>
    </section>
  </main>
</template>
