package database

import (
	"os"
	"time"

	"gorm.io/gorm"
)

type ModelParams struct {
	BaseUrl string `json:"base_url"`
	Token   string `json:"token"`
	Model   string `json:"model"`
	Limit   int    `json:"limit"`
}

// Model 模型表
type Model struct {
	ModelID   string `gorm:"primaryKey;column:model_id" json:"model_id"`   // 模型ID
	Username  string `gorm:"column:username;not null" json:"username"`     // 创建者用户名
	ModelName string `gorm:"column:model_name;not null" json:"model_name"` // 模型名称
	Token     string `gorm:"column:token;not null" json:"token"`           // API Token
	BaseURL   string `gorm:"column:base_url;not null" json:"base_url"`     // 基础URL
	Note      string `gorm:"column:note" json:"note"`                      // 备注信息
	Limit     int    `gorm:"column:limit" json:"limit"`
	CreatedAt int64  `gorm:"column:created_at;not null" json:"created_at"` // 时间戳毫秒级
	UpdatedAt int64  `gorm:"column:updated_at;not null" json:"updated_at"` // 时间戳毫秒级

	// 关联关系
	User User `gorm:"foreignKey:Username" json:"user"`
}

// ModelStore 模型数据存储
type ModelStore struct {
	db *gorm.DB
}

// NewModelStore 创建新的ModelStore实例
func NewModelStore(db *gorm.DB) *ModelStore {
	return &ModelStore{db: db}
}

// Init 自动迁移模型相关表结构
func (s *ModelStore) Init() error {
	return s.db.AutoMigrate(&Model{})
}

// CreateModel 创建模型
func (s *ModelStore) CreateModel(model *Model) error {
	now := time.Now().UnixMilli()
	model.CreatedAt = now
	model.UpdatedAt = now
	return s.db.Create(model).Error
}

// GetModel 获取模型信息
func (s *ModelStore) GetModel(modelID string) (*Model, error) {
	var model Model
	err := s.db.Preload("User").First(&model, "model_id = ?", modelID).Error
	if err != nil {
		return nil, err
	}
	return &model, nil
}

// GetModelByUser 获取用户创建的模型
func (s *ModelStore) GetModelByUser(modelID string, username string) (*Model, error) {
	var model Model
	err := s.db.Preload("User").First(&model, "model_id = ? AND username = ?", modelID, username).Error
	if err != nil {
		return nil, err
	}
	return &model, nil
}

// GetAllModels 获取所有模型
func (s *ModelStore) GetAllModels() ([]*Model, error) {
	var models []*Model
	err := s.db.Preload("User").Order("created_at DESC").Find(&models).Error
	if err != nil {
		return nil, err
	}
	return models, nil
}

// GetUserModels 获取用户的所有模型
func (s *ModelStore) GetUserModels(username string) ([]*Model, error) {
	var models []*Model
	err := s.db.Preload("User").Where("username = ?", username).Order("created_at DESC").Find(&models).Error
	if err != nil {
		return nil, err
	}
	return models, nil
}

// UpdateModel 更新模型信息
func (s *ModelStore) UpdateModel(modelID string, username string, updates map[string]interface{}) error {
	// 添加更新时间
	updates["updated_at"] = time.Now().UnixMilli()
	return s.db.Model(&Model{}).Where("model_id = ? AND username = ?", modelID, username).Updates(updates).Error
}

// DeleteModel 删除模型
func (s *ModelStore) DeleteModel(modelID string, username string) error {
	return s.db.Delete(&Model{}, "model_id = ? AND username = ?", modelID, username).Error
}

// BatchDeleteModels 批量删除模型
func (s *ModelStore) BatchDeleteModels(modelIDs []string, username string) (int64, error) {
	result := s.db.Delete(&Model{}, "model_id IN ? AND username = ?", modelIDs, username)
	return result.RowsAffected, result.Error
}

// CheckModelExists 检查模型是否存在
func (s *ModelStore) CheckModelExists(modelID string) (bool, error) {
	var count int64
	err := s.db.Model(&Model{}).Where("model_id = ?", modelID).Count(&count).Error
	return count > 0, err
}

// CheckModelExistsByUser 检查用户是否拥有该模型
func (s *ModelStore) CheckModelExistsByUser(modelID string, username string) (bool, error) {
	var count int64
	err := s.db.Model(&Model{}).Where("model_id = ? AND username = ?", modelID, username).Count(&count).Error
	return count > 0, err
}

func (s *ModelStore) AutoAddModels() {
	// 判断如果模型为空，并且环境变量存在 model token base_url，则自动添加模型
	if s.db == nil {
		return
	}
	var count int64
	s.db.Model(&Model{}).Count(&count)
	if count == 0 {
		model := os.Getenv("MODEL")
		token := os.Getenv("TOKEN")
		baseUrl := os.Getenv("BASE_URL")
		if model != "" && token != "" && baseUrl != "" {
			s.CreateModel(&Model{
				ModelID:   "system_default",
				Username:  "",
				ModelName: model,
				Token:     token,
				BaseURL:   baseUrl,
				Note:      "系统默认内置",
				CreatedAt: time.Now().UnixMilli(),
				UpdatedAt: time.Now().UnixMilli(),
			})
		}
	}
}
