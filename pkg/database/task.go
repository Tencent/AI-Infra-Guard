package database

import (
	"encoding/json"
	"fmt"
	"time"

	"gorm.io/datatypes"
	"gorm.io/gorm"
)

// User 用户表
type User struct {
	Username  string `gorm:"primaryKey;column:username" json:"username"`
	CreatedAt int64  `gorm:"column:created_at;not null" json:"created_at"` // 时间戳毫秒级
	UpdatedAt int64  `gorm:"column:updated_at;not null" json:"updated_at"` // 时间戳毫秒级
}

// Session 会话表（一个会话对应一个任务）
type Session struct {
	ID             string         `gorm:"primaryKey;column:id" json:"id"` // 会话ID，也是任务ID
	Username       string         `gorm:"column:username;not null" json:"username"`
	Title          string         `gorm:"column:title" json:"title"`
	TaskType       string         `gorm:"column:task_type;not null" json:"task_type"`          // 任务类型
	Content        string         `gorm:"column:content;not null" json:"content"`              // 任务内容
	Params         datatypes.JSON `gorm:"column:params" json:"params"`                         // 任务参数
	Attachments    datatypes.JSON `gorm:"column:attachments" json:"attachments"`               // 附件
	Status         string         `gorm:"column:status;not null;default:'todo'" json:"status"` // todo, doing, done, error
	AssignedAgent  string         `gorm:"column:assigned_agent" json:"assigned_agent"`         // 分配的Agent
	CountryIsoCode string         `gorm:"column:contry_iso_code" json:"countryIsoCode"`        // 标识语言
	StartedAt      *int64         `gorm:"column:started_at" json:"started_at"`                 // 时间戳毫秒级
	CompletedAt    *int64         `gorm:"column:completed_at" json:"completed_at"`             // 时间戳毫秒级
	CreatedAt      int64          `gorm:"column:created_at;not null" json:"created_at"`        // 时间戳毫秒级
	UpdatedAt      int64          `gorm:"column:updated_at;not null" json:"updated_at"`        // 时间戳毫秒级

	// 关联关系
	User     User          `gorm:"foreignKey:Username" json:"user"`
	Messages []TaskMessage `gorm:"foreignKey:SessionID" json:"messages"` // 直接关联到Session
	Share    bool          `gorm:"column:share;not null;default:false" json:"share"`
}

// TaskMessage 任务消息表（存储所有类型的事件消息）
type TaskMessage struct {
	ID        string         `gorm:"primaryKey;column:id" json:"id"`               // 消息ID（前端生成的对话ID）
	SessionID string         `gorm:"column:session_id;not null" json:"session_id"` // 会话ID（也是任务ID）
	Type      string         `gorm:"column:type;not null" json:"type"`             // liveStatus, planUpdate, statusUpdate, toolUsed等
	EventData datatypes.JSON `gorm:"column:event_data;not null" json:"event_data"` // 存储事件的具体数据
	Timestamp int64          `gorm:"column:timestamp;not null" json:"timestamp"`
	CreatedAt int64          `gorm:"column:created_at;not null" json:"created_at"` // 时间戳毫秒级

	// 关联关系
	Session Session `gorm:"foreignKey:SessionID" json:"session"`
}

// TaskStore 任务数据存储
type TaskStore struct {
	db *gorm.DB
}

// NewTaskStore 创建新的TaskStore实例
func NewTaskStore(db *gorm.DB) *TaskStore {
	return &TaskStore{db: db}
}

// Init 自动迁移任务相关表结构
func (s *TaskStore) Init() error {
	return s.db.AutoMigrate(&User{}, &Session{}, &TaskMessage{})
}

// CreateUser 创建用户
func (s *TaskStore) CreateUser(user *User) error {
	now := time.Now().UnixMilli()
	user.CreatedAt = now
	user.UpdatedAt = now
	return s.db.Create(user).Error
}

// ResetRunningTasks 重置运行中的任务为失败
func (s *TaskStore) ResetRunningTasks() error {
	return s.db.Model(&Session{}).Where("status = 'doing' or status = 'failed'").Updates(map[string]interface{}{
		"status":     "error",
		"updated_at": time.Now().UnixMilli(),
	}).Error
}

// GetUser 获取用户信息
func (s *TaskStore) GetUser(username string) (*User, error) {
	var user User
	err := s.db.First(&user, "username = ?", username).Error
	if err != nil {
		return nil, err
	}
	return &user, nil
}

// CreateSession 创建会话（包含任务信息）
func (s *TaskStore) CreateSession(session *Session) error {
	now := time.Now().UnixMilli()
	session.CreatedAt = now
	session.UpdatedAt = now
	return s.db.Create(session).Error
}

// GetSession 获取会话信息
func (s *TaskStore) GetSession(id string) (*Session, error) {
	var session Session
	err := s.db.Preload("User").Preload("Messages").First(&session, "id = ?", id).Error
	if err != nil {
		return nil, err
	}
	return &session, nil
}

// SetShare 设置会话共享
func (s *TaskStore) SetShare(sessionID string, share bool) error {
	return s.db.Model(&Session{}).Where("id = ?", sessionID).Update("share", share).Error
}

// UpdateSessionStatus 更新会话状态
func (s *TaskStore) UpdateSessionStatus(id string, status string) error {
	now := time.Now().UnixMilli()
	updates := map[string]interface{}{
		"status":     status,
		"updated_at": now,
	}

	if status == "doing" {
		updates["started_at"] = &now
	} else if status == "done" {
		updates["completed_at"] = &now
	}

	return s.db.Model(&Session{}).Where("id = ?", id).Updates(updates).Error
}

// UpdateSessionAssignedAgent 更新会话的分配Agent和开始时间
func (s *TaskStore) UpdateSessionAssignedAgent(sessionID string, agentID string) error {
	now := time.Now().UnixMilli()
	updates := map[string]interface{}{
		"assigned_agent": agentID,
		"status":         "doing",
		"started_at":     &now,
	}

	return s.db.Model(&Session{}).Where("id = ?", sessionID).Updates(updates).Error
}

// UpdateSession 更新会话信息
func (s *TaskStore) UpdateSession(sessionID string, updates map[string]interface{}) error {
	// 添加更新时间
	updates["updated_at"] = time.Now().UnixMilli()
	return s.db.Model(&Session{}).Where("id = ?", sessionID).Updates(updates).Error
}

// DeleteSession 删除会话
func (s *TaskStore) DeleteSession(sessionID string) error {
	return s.db.Delete(&Session{}, "id = ?", sessionID).Error
}

// DeleteSessionMessages 删除会话的所有消息
func (s *TaskStore) DeleteSessionMessages(sessionID string) error {
	return s.db.Where("session_id = ?", sessionID).Delete(&TaskMessage{}).Error
}

// DeleteSessionWithMessages 使用事务删除会话及其所有消息
func (s *TaskStore) DeleteSessionWithMessages(sessionID string) error {
	return s.db.Transaction(func(tx *gorm.DB) error {
		// 1. 删除会话的所有消息
		if err := tx.Where("session_id = ?", sessionID).Delete(&TaskMessage{}).Error; err != nil {
			return fmt.Errorf("删除会话消息失败: %v", err)
		}

		// 2. 删除会话记录
		if err := tx.Delete(&Session{}, "id = ?", sessionID).Error; err != nil {
			return fmt.Errorf("删除会话记录失败: %v", err)
		}

		return nil
	})
}

// CreateTaskMessage 创建任务消息
func (s *TaskStore) CreateTaskMessage(message *TaskMessage) error {
	now := time.Now().UnixMilli()
	message.CreatedAt = now
	return s.db.Create(message).Error
}

// GetSessionMessages 获取会话的所有消息
func (s *TaskStore) GetSessionMessages(sessionID string) ([]*TaskMessage, error) {
	var messages []*TaskMessage
	err := s.db.Where("session_id = ?", sessionID).Order("timestamp ASC").Find(&messages).Error
	if err != nil {
		return nil, err
	}
	return messages, nil
}

// GetUserSessions 获取用户的所有会话
func (s *TaskStore) GetUserSessions(username string) ([]*Session, error) {
	var sessions []*Session
	err := s.db.Where("username = ?", username).Order("created_at DESC").Find(&sessions).Error
	if err != nil {
		return nil, err
	}
	return sessions, nil
}

// GetUserSessionsByType 获取用户的会话，支持可选的任务类型过滤
func (s *TaskStore) GetUserSessionsByType(username string, taskType string) ([]*Session, error) {
	query := s.db.Where("username = ?", username)

	// 如果指定了任务类型，添加类型过滤
	if taskType != "" {
		query = query.Where("task_type = ?", taskType)
	}

	var sessions []*Session
	err := query.Order("created_at DESC").Find(&sessions).Error
	if err != nil {
		return nil, err
	}
	return sessions, nil
}

// StoreEvent 存储事件消息
func (s *TaskStore) StoreEvent(id string, sessionID string, eventType string, eventData interface{}, timestamp int64) error {
	// 将事件数据序列化为JSON
	eventJSON, err := json.Marshal(eventData)
	if err != nil {
		return err
	}

	message := &TaskMessage{
		ID:        id,
		SessionID: sessionID,
		Type:      eventType,
		EventData: datatypes.JSON(eventJSON),
		Timestamp: timestamp,
	}

	return s.CreateTaskMessage(message)
}

// GetSessionEvents 获取会话的所有事件
func (s *TaskStore) GetSessionEvents(sessionID string) ([]*TaskMessage, error) {
	return s.GetSessionMessages(sessionID)
}

// GetSessionEventsByType 根据类型获取会话事件
func (s *TaskStore) GetSessionEventsByType(sessionID string, eventType string) ([]*TaskMessage, error) {
	var messages []*TaskMessage
	err := s.db.Where("session_id = ? AND type = ?", sessionID, eventType).Order("timestamp ASC").Find(&messages).Error
	if err != nil {
		return nil, err
	}
	return messages, nil
}

// SearchUserSessionsSimple 使用单个查询参数搜索用户的会话，支持在title、content、task_type字段中搜索
func (s *TaskStore) SearchUserSessionsSimple(username string, searchParams SimpleSearchParams) ([]*Session, int64, error) {
	query := s.db.Model(&Session{}).Where("username = ?", username)

	// 如果指定了任务类型，添加类型过滤
	if searchParams.TaskType != "" {
		query = query.Where("task_type = ?", searchParams.TaskType)
	}

	// 如果有查询关键词，在多个字段中搜索
	if searchParams.Query != "" {
		query = query.Where("title LIKE ? OR content LIKE ? OR task_type LIKE ?",
			"%"+searchParams.Query+"%",
			"%"+searchParams.Query+"%",
			"%"+searchParams.Query+"%")
	}

	// 获取总数
	var total int64
	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	// 应用分页和排序
	var sessions []*Session
	err := query.Order("created_at DESC").
		Offset((searchParams.Page - 1) * searchParams.PageSize).
		Limit(searchParams.PageSize).
		Find(&sessions).Error

	if err != nil {
		return nil, 0, err
	}

	return sessions, total, nil
}

// SimpleSearchParams 简化搜索参数结构
type SimpleSearchParams struct {
	Query    string `json:"query"`     // 查询关键词，将在title、content、task_type字段中搜索
	TaskType string `json:"task_type"` // 任务类型过滤
	Page     int    `json:"page"`      // 页码
	PageSize int    `json:"page_size"` // 每页大小
}

// generateMessageID 生成消息ID
func generateMessageID() string {
	return time.Now().Format("20060102150405") + "_" + fmt.Sprintf("%d", time.Now().UnixNano())
}
