package database

import (
	"time"

	"gorm.io/datatypes"
	"gorm.io/gorm"
)

// Agent 表示一个注册的agent（GORM实现）
type Agent struct {
	ID           string         `gorm:"primaryKey;column:id" json:"agent_id"`
	Hostname     string         `gorm:"column:hostname;not null" json:"hostname"`
	IP           string         `gorm:"column:ip;not null" json:"ip"`
	Version      string         `gorm:"column:version" json:"version"`
	Capabilities datatypes.JSON `gorm:"column:capabilities" json:"capabilities"` // 存储为JSON
	Meta         string         `gorm:"column:meta;not null" json:"meta"`
	LastSeen     time.Time      `gorm:"column:last_seen;not null" json:"last_seen"`
	CreatedAt    time.Time      `gorm:"column:created_at;not null" json:"created_at"`
	UpdatedAt    time.Time      `gorm:"column:updated_at;not null" json:"updated_at"`
	Online       bool           `gorm:"column:online;not null;default:false" json:"online"`
}

type AgentStore struct {
	db *gorm.DB
}

// NewAgentStore 创建一个新的AgentStore实例
func NewAgentStore(db *gorm.DB) *AgentStore {
	return &AgentStore{db: db}
}

// Init 自动迁移agent表结构
func (s *AgentStore) Init() error {
	return s.db.AutoMigrate(&Agent{})
}

// Register 注册或更新agent信息
func (s *AgentStore) Register(agent *Agent) error {
	now := time.Now()
	agent.LastSeen = now
	if agent.CreatedAt.IsZero() {
		agent.CreatedAt = now
	}
	agent.UpdatedAt = now
	return s.db.Save(agent).Error
}

// GetAgent 获取指定agent的信息
func (s *AgentStore) GetAgent(id string) (*Agent, error) {
	var agent Agent
	err := s.db.First(&agent, "id = ?", id).Error
	if err != nil {
		return nil, err
	}
	return &agent, nil
}

// ListAgents 获取所有agent列表
func (s *AgentStore) ListAgents() ([]*Agent, error) {
	var agents []*Agent
	err := s.db.Find(&agents).Error
	if err != nil {
		return nil, err
	}
	return agents, nil
}

// UpdateLastSeen 更新agent的最后在线时间
func (s *AgentStore) UpdateLastSeen(id string) error {
	return s.db.Model(&Agent{}).Where("id = ?", id).Updates(map[string]interface{}{
		"last_seen":  time.Now(),
		"updated_at": time.Now(),
	}).Error
}

// DeleteAgent 删除指定的agent
func (s *AgentStore) DeleteAgent(id string) error {
	return s.db.Delete(&Agent{}, "id = ?", id).Error
}

func (s *AgentStore) UpdateOnlineStatus(id string, online bool) error {
	return s.db.Model(&Agent{}).Where("id = ?", id).Update("online", online).Error
}
