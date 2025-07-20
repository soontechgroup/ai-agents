# 详细设计方案

## 游戏配置设计

### Dice 游戏配置结构设计

状态：⚠️ 待实现

#### 设计目标

1. **简洁性**: 避免数据冗余，移除不必要的 currencies 数组
2. **性能**: 支持快速查询特定货币配置
3. **合规性**: 确保 RTP 配置透明且合规
4. **可维护性**: 清晰的数据结构，便于添加新货币

#### 配置数据结构

```typescript
interface DiceGameConfig {
  // 游戏基本信息
  gameInfo: {
    gameId: string | null;
    gameIcon: string;
    gameName: string;
  };
  
  // 货币投注配置
  betInfo: Array<{
    currency: string;     // 货币代码
    defaultBet: number;   // 默认投注额
    minBet: number;       // 最小投注额
    maxBet: number;       // 最大投注额
    maxProfit: number;    // 最大盈利限制
  }>;
  
  // RTP配置
  rtpConfig: {
    displayRTP: number[];  // 显示给用户的RTP选项
    actualRTP: number[];   // 实际可用的RTP值
  };
  
  // 游戏参数
  gameParameters: {
    rollSliderRange: {
      min: number;
      max: number;
    };
    rollNumberRange: {
      min: number;
      max: number;
    };
  };
}
```

#### 优化要点

1. **移除冗余数据**
   - 删除了原有的 `currencies` 数组
   - 货币列表可从 `betInfo` 动态提取

2. **保持有序性**
   - `betInfo` 数组保持原有顺序
   - 货币显示顺序与数组顺序一致

3. **RTP合规性改进**
   - `displayRTP` 值必须是 `actualRTP` 的子集
   - 建议统一显示和实际RTP，避免误导用户

4. **性能优化策略**
   ```javascript
   // 应用层构建索引
   class DiceConfigService {
     private betInfoMap: Map<string, BetInfo>;
     
     constructor(config: DiceGameConfig) {
       this.betInfoMap = new Map();
       config.betInfo.forEach(info => {
         this.betInfoMap.set(info.currency, info);
       });
     }
     
     getBetInfo(currency: string): BetInfo | undefined {
       return this.betInfoMap.get(currency);
     }
   }
   ```

#### 数据验证规则

1. **投注金额验证**
   - `minBet <= defaultBet <= maxBet`
   - `maxProfit <= maxBet * 最大可能倍数`

2. **RTP验证**
   - `displayRTP` 所有值必须存在于 `actualRTP` 中
   - RTP值范围：75% - 99%

3. **游戏参数验证**
   - `rollSliderRange.min >= 0.01`
   - `rollSliderRange.max <= 99.99`
   - `rollNumberRange` 应覆盖 `rollSliderRange`

## 其他设计方案

待完善...