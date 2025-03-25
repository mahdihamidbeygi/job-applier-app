import { ChatOllama } from '@langchain/community/chat_models/ollama';
import { HumanMessage } from '@langchain/core/messages';

export class OllamaService {
  constructor() {
    this.llm = new ChatOllama({
      model: 'phi4',
      temperature: 0.2,
      baseUrl: 'http://localhost:11434',
    });
  }

  async invoke(messages) {
    return await this.llm.invoke(messages);
  }

  async call(prompt) {
    return await this.llm.invoke([new HumanMessage(prompt)]);
  }
} 