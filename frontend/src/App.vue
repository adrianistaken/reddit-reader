<script setup>
import { ref, onMounted } from "vue";

const posts = ref([]);

// Fetch data from the Flask API when the component is mounted
const fetchPosts = async () => {
    try {
        const response = await fetch("http://127.0.0.1:5000/api/posts"); // Change this to your deployed backend URL when live
        posts.value = await response.json();
    } catch (error) {
        console.error("Error fetching posts:", error);
    }
};

// Call the function when the component is mounted
onMounted(fetchPosts);
</script>

<template>
    <div class="container">
        <h1>📌 Dota 2 Reddit Posts</h1>

        <div v-if="posts.length === 0" class="loading">
            <p>Loading posts...</p>
        </div>

        <div v-else>
            <div v-for="(post, index) in posts" :key="index" class="post">
                <h2>{{ post.title }}</h2>
                <p>
                    <strong>🏷 Flair:</strong> {{ post.flair }} |
                    📆 {{ post.created_at }} |
                    👍 {{ post.score }} |
                    💬 {{ post.comments }}
                </p>
                <a :href="post.url" target="_blank" class="reddit-link">🔗 Read on Reddit</a>
            </div>
        </div>
    </div>
</template>

<style scoped>
.container {
    max-width: 800px;
    margin: 20px auto;
    font-family: Arial, sans-serif;
}

h1 {
    text-align: center;
}

.loading {
    text-align: center;
    font-size: 18px;
    color: gray;
}

.post {
    border-bottom: 1px solid #ddd;
    padding: 15px 0;
}

.reddit-link {
    color: #0079d3;
    text-decoration: none;
    font-weight: bold;
}

.reddit-link:hover {
    text-decoration: underline;
}
</style>
