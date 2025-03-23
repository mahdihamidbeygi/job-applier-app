import { ChatOpenAI } from '@langchain/openai';
import { BaseMessage, HumanMessage } from '@langchain/core/messages';

export class OpenAIService {
  private llm: ChatOpenAI;

  constructor() {
    this.llm = new ChatOpenAI({
      modelName: 'gpt-4',
      temperature: 0.2,
    });
  }

  async invoke(messages: BaseMessage[]) {
    return await this.llm.invoke(messages);
  }

  async call(prompt: string) {
    return await this.llm.invoke([new HumanMessage(prompt)]);
  }
} 