<template>
    <div class="chat-area">
        <div class="messages-area">
            <MessageBubble :message="message" v-for="message in messages" :key="message.id" />
        </div>
        <div class="input-area">
            <div ref="senderRef"></div>
            <button>发送</button>
        </div>
    </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue';
import XSender from 'x-sender';
import "x-sender/style"
import MessageBubble from '@/components/MessageBubble.vue';

let sender = null;
const senderRef = ref(null);
const messages = ref([
    { role: 'user', content: '你好', type: 'user' },
    { role: 'assistant', content: '你好！有什么我可以帮助你的吗？', type: 'model' },
    { role: 'user', content: '北京天气怎么样', type: 'user' },
    { role: 'assistant', content: '我需要查询北京的天气', type: 'model' },
    { role: 'tool', content: '使用工具get_weather，参数：{"location": "北京"}', type: 'tool_use' },
    { role: 'tool', content: '北京天气晴朗，温度25摄氏度', type: 'tool_result' },
    { role: 'assistant', content: '北京天气晴朗，温度25摄氏度', type: 'model' },
]);

onMounted(() => {
    sender = new XSender(senderRef.value, {
        chatStyle: {
            height: '80px',
            maxHeight: '80px',
        },
        placeholder: '请输入消息...'
    });
});

onBeforeUnmount(() => {
    if (sender) {
        sender.destroy();
    }
});
</script>

<style scoped>
.chat-area {
    height: 100%;
    display: flex;
    flex-direction: column;
}
.messages-area {
    flex: 1;
    overflow-y: auto;
}
</style>