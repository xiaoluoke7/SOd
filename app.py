import streamlit as st
import ollama
import io # 用于处理文件内容
import base64 # 导入 base64 库用于编码图片

# 设置 Ollama 服务的地址
# 明确指定连接到本地的 Ollama 服务
client = ollama.Client(host='http://localhost:11434')

    # 设置页面标题
st.title("------------AI对话助手------------")

    # 初始化聊天历史
if "messages" not in st.session_state:
        st.session_state.messages = []

    # 在应用重新运行时显示历史消息
for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- 文件上传组件 ---
uploaded_file = st.file_uploader("上传文件 (可选，内容将作为上下文提供给 AI)", type=None) # type=None 允许上传任何类型文件，你也可以指定 ['txt', 'pdf', 'csv'] 等

file_content = None
image_content_base64 = None # 用于存储 Base64 编码后的图片内容

if uploaded_file is not None:
    # 检查文件类型，简单判断是否为图片
    if uploaded_file.type and uploaded_file.type.startswith('image/'):
        try:
            # 读取图片二进制内容并进行 Base64 编码
            image_bytes = uploaded_file.getvalue()
            image_content_base64 = base64.b64encode(image_bytes).decode('utf-8')
            st.success(f"图片 '{uploaded_file.name}' 已上传并编码。")
            # 对于图片，不将其内容作为文本附加到提示词，而是作为单独的参数传递
            file_content = None # 清空 file_content
        except Exception as e:
            st.error(f"处理图片 '{uploaded_file.name}' 时发生错误: {e}")
            image_content_base64 = None

    else:
        # 简单的文本文件内容读取和解码 (保留原有逻辑)
        try:
            # 使用 io.BytesIO 包装 uploaded_file 以便读取
            # 注意：这里假设是文本文件。对于PDF等需要额外的库来读取内容。
            # 对于大文件，一次性读取到内存可能会有问题，需要考虑分块处理。
            stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
            file_content = stringio.read()
            st.success(f"文件 '{uploaded_file.name}' 已上传并读取内容。内容将作为上下文发送给模型。")
            # 可以选择显示部分文件内容作为确认
            # st.text_area("文件内容预览:", file_content[:500] + "..." if len(file_content) > 500 else file_content)
            image_content_base64 = None # 清空 image_content_base64

        except Exception as e:
            st.error(f"读取文件 '{uploaded_file.name}' 时发生错误: {e}")
            file_content = None # 读取失败则清空内容
            image_content_base64 = None

    # --- 用户输入和生成响应 ---
if prompt := st.chat_input("输入你的消息..."):
        # 将用户消息添加到聊天历史
        st.session_state.messages.append({"role": "user", "content": prompt})
        # 在聊天界面显示用户消息
        with st.chat_message("user"):
            st.markdown(prompt)

        # 构建发送给 Ollama 的消息
        # 添加指令，要求模型用中文回复
        chinese_instruction = "请用中文回复。\n"

        messages_payload = [
            {'role': m['role'], 'content': m['content']}
            for m in st.session_state.messages[:-1]
        ] # 发送除了当前用户消息之外的所有历史消息

        current_message_content = chinese_instruction + prompt

        if file_content:
            # 将文本文件内容作为上下文添加到当前提示中
            current_message_content = f"{chinese_instruction}请参考以下文件内容：\n```\n{file_content}\n```\n\n用户的问题/指令是：{prompt}"
            st.info("文本文件内容已添加到当前提示中发送给模型。") # 给用户一个提示

        # 构建发送给 Ollama 的 messages 列表
        message_to_send = {'role': 'user', 'content': current_message_content}

        if image_content_base64:
            # 如果有图片，将其添加到消息负载中
            # 注意：Ollama 的 images 参数是一个 Base64 编码字符串的列表
            message_to_send['images'] = [image_content_base64]
            st.info("图片已添加到当前提示中发送给模型。") # 给用户一个提示

        messages_payload.append(message_to_send)

        # 调用 Ollama 模型生成响应
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            try:
                # 使用 client 对象调用 chat 方法
                stream = client.chat(
                    model='gemma3:27b-it-q8_0', # 请将 'llama2' 替换为你本地的 Ollama 模型名称
                    messages=messages_payload,
                    stream=True,
                )
                for chunk in stream:
                    if chunk['message']['content'] is not None:
                        full_response += chunk['message']['content']
                        message_placeholder.markdown(full_response + "▌") # 显示流式响应

                message_placeholder.markdown(full_response) # 显示最终响应

            except Exception as e:
                 st.error(f"调用 Ollama 模型时发生错误: {e}")
                 full_response = "无法获取响应。"

            # 将助手的响应添加到聊天历史
            st.session_state.messages.append({"role": "assistant", "content": full_response})

