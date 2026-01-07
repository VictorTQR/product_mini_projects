<template>
    <div class="message-bubble">
        <div class="message-content">{{ message.content }}</div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
    message: {
        type: Object,
        default: () => ({})
    }
});
</script>

<style scoped>
.message-bubble {
    padding: 10px;
    border-radius: 10px;
    margin-bottom: 10px;
}
</style>
