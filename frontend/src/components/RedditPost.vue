<template>
    <div>
        <div class="card bg-base-300 shadow-sm m-auto my-6 text-left">
            <div class="card-body gap-3">
                <!-- Post author -->
                <div class="flex items-center gap-2">
                    <a :href="`https://reddit.com/user/${post.author_name}`" target="_blank">
                        <img :src="post.author_image" alt="" class="rounded-full w-7 m-auto">
                    </a>

                    <a :href="`https://reddit.com/user/${post.author_name}`" target="_blank">
                        <p class="text-center">{{ post.author_name }}</p>
                    </a>

                    • {{ post.created_at }}
                </div>

                <!-- Post title -->
                <a :href="`https://reddit.com${post.permalink}`" target="_blank" class="card-title w-fit">
                    <h2>{{ post.title }}</h2>
                </a>

                <!-- Post flair -->
                <span class="badge bg-[#414e68]">{{ post.flair }}</span>

                <!-- Post content -->
                <div class="relative w-full flex justify-center items-center overflow-hidden rounded-md">

                    <!-- ✅ Image Post with Blurred Extensions -->
                    <template v-if="post.media_type === 'image'">
                        <img :src="post.media_url" class="relative z-10 max-w-full h-auto object-cover" />

                        <!-- Left blurred extension -->
                        <div class="absolute left-0 top-0 h-full w-1/4 bg-no-repeat bg-left transform scale-x-[-1] blur-xl opacity-80"
                            :style="{ backgroundImage: `url(${post.media_url})` }"></div>

                        <!-- Right blurred extension -->
                        <div class="absolute right-0 top-0 h-full w-1/4 bg-no-repeat bg-right blur-xl opacity-80"
                            :style="{ backgroundImage: `url(${post.media_url})` }"></div>
                    </template>

                    <!-- ✅ Reddit Video -->
                    <video v-else-if="post.media_type === 'video'" :src="post.media_url" controls
                        class="max-w-full h-auto rounded-md"></video>

                    <!-- ✅ YouTube Video Embed -->
                    <iframe v-else-if="post.media_type === 'youtube'"
                        :src="post.media_url.replace('watch?v=', 'embed/')" class="max-w-full h-auto rounded-md"
                        frameborder="0" allowfullscreen></iframe>

                    <!-- ✅ External Image (Imgur, Gfycat, etc.) -->
                    <img v-else-if="post.media_type === 'external_image'" :src="post.media_url"
                        class="max-w-full h-auto object-cover rounded-md" />

                    <!-- ✅ Ensure this only applies to text posts -->
                    <p v-else-if="post.media_type === 'text'" class="py-4 rounded-md">
                        {{ truncatedText }}
                    </p>

                    <!-- ✅ External Link -->
                    <a v-else :href="post.media_url" target="_blank">
                        <button class="btn btn-warning">View Post</button>
                    </a>

                </div>


                <!-- Post stats -->
                <div>
                    <span class="badge">
                        <svg rpl="" fill="currentColor" height="16" icon-name="upvote-outline" viewBox="0 0 20 20"
                            width="16" xmlns="http://www.w3.org/2000/svg">
                            <path
                                d="M10 19c-.072 0-.145 0-.218-.006A4.1 4.1 0 0 1 6 14.816V11H2.862a1.751 1.751 0 0 1-1.234-2.993L9.41.28a.836.836 0 0 1 1.18 0l7.782 7.727A1.751 1.751 0 0 1 17.139 11H14v3.882a4.134 4.134 0 0 1-.854 2.592A3.99 3.99 0 0 1 10 19Zm0-17.193L2.685 9.071a.251.251 0 0 0 .177.429H7.5v5.316A2.63 2.63 0 0 0 9.864 17.5a2.441 2.441 0 0 0 1.856-.682A2.478 2.478 0 0 0 12.5 15V9.5h4.639a.25.25 0 0 0 .176-.429L10 1.807Z">
                            </path>
                        </svg>
                        {{ post.score }}
                    </span>
                    <span class="badge">
                        <svg rpl="" aria-hidden="true" class="icon-comment" fill="currentColor" height="16"
                            icon-name="comment-outline" viewBox="0 0 20 20" width="16"
                            xmlns="http://www.w3.org/2000/svg">
                            <path
                                d="M10 19H1.871a.886.886 0 0 1-.798-.52.886.886 0 0 1 .158-.941L3.1 15.771A9 9 0 1 1 10 19Zm-6.549-1.5H10a7.5 7.5 0 1 0-5.323-2.219l.54.545L3.451 17.5Z">
                            </path>
                        </svg>
                        {{ post.comments }}
                    </span>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { computed } from 'vue';
import { toRefs } from 'vue';

const props = defineProps({
    post: {
        type: Object,
        required: true
    }
});

const { post } = toRefs(props);

const MAX_LENGTH = 300; // Set character limit

// ✅ Function to truncate text safely
const truncatePostText = (text, limit) => {
    if (!text) return ""; // Prevent errors if text is missing
    return text.length > limit ? text.slice(0, limit) + "..." : text;
};

// ✅ Compute truncated text
const truncatedText = computed(() => truncatePostText(post.value.text_content, MAX_LENGTH));
</script>

<style></style>