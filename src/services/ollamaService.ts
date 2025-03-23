import { ChatOllama } from '@langchain/community/chat_models/ollama';
import { BaseMessage, HumanMessage } from '@langchain/core/messages';

export class OllamaService {
  private llm: ChatOllama;

  constructor() {
    this.llm = new ChatOllama({
      model: 'phi4',
      temperature: 0.2,
      baseUrl: 'http://localhost:11434',
    });
  }

  async invoke(messages: BaseMessage[]) {
    return await this.llm.invoke(messages);
  }

  async call(prompt: string) {
    return await this.llm.invoke([new HumanMessage(prompt)]);
  }
} 