<script setup>
import { ref, onMounted } from "vue";
import RedditPost from "./components/RedditPost.vue";

const posts = ref([]);

// Fetch data from the Flask API when the component is mounted
const fetchPosts = async () => {
    try {
        const response = await fetch("https://reddit-reader-ydlg.onrender.com/api/posts"); // Change this to your deployed backend URL when live
        posts.value = await response.json();
    } catch (error) {
        console.error("Error fetching posts:", error);
    }
};

// Call the function when the component is mounted
onMounted(fetchPosts);
</script>

<template>
    <div class="text-center m-auto max-w-5xl md:w-3xl w-full">
        <h1>📌 Dota 2 Reddit Posts</h1>

        <div class="flex flex-col">
            <div v-if="posts.length === 0" class="p-10">
                <div class="loading mb-5"></div>
                <p>Loading posts... it takes about 40 seconds on first load..</p>
            </div>

            <div v-else>
                <div v-for="(post, index) in posts" :key="index" class="post">
                    <RedditPost :post="post" />
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped></style>
