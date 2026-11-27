package websocket

import (
	"encoding/json"
	"os"
	"testing"

	"github.com/Tencent/AI-Infra-Guard/common/agent"
	"github.com/Tencent/AI-Infra-Guard/pkg/database"
	"github.com/stretchr/testify/require"
)

func resultEvent(target, fp string, cves ...string) map[string]interface{} {
	vulns := make([]interface{}, 0, len(cves))
	for _, c := range cves {
		vulns = append(vulns, map[string]interface{}{"cve": c})
	}
	return map[string]interface{}{
		"result": map[string]interface{}{
			"results": []interface{}{
				map[string]interface{}{"target_url": target, "fingerprint": fp, "vulnerabilities": vulns},
			},
		},
	}
}

func TestClassifyReverify(t *testing.T) {
	target, cve := "http://t", "CVE-1"

	state, rep, _ := classifyReverify(resultEvent(target, "nginx/1.0", cve), target, cve, false)
	require.Equal(t, "reproduced", state)
	require.True(t, rep)

	state, rep, _ = classifyReverify(resultEvent(target, "nginx/2.0"), target, cve, false)
	require.Equal(t, "fixed", state)
	require.False(t, rep)

	state, _, _ = classifyReverify(resultEvent(target, ""), target, cve, false)
	require.Equal(t, "error", state) // reachable but not fingerprinted

	state, _, _ = classifyReverify(resultEvent(target, "nginx", cve), target, cve, false)
	require.Equal(t, "error", state) // CVE claimed but the fingerprint has no version evidence

	// AI source: absent CVE in a deterministic re-run cannot be called "fixed".
	state, _, _ = classifyReverify(resultEvent(target, "nginx/2.0"), target, cve, true)
	require.Equal(t, "error", state)

	state, _, _ = classifyReverify(map[string]interface{}{"result": map[string]interface{}{"results": []interface{}{}}}, target, cve, false)
	require.Equal(t, "error", state) // no entry for the target

	state, _, _ = classifyReverify("garbage", target, cve, false)
	require.Equal(t, "error", state)
}

func TestCopyAttachmentsShadow(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()
	dir := t.TempDir()
	tm.fileConfig = &FileUploadConfig{UploadDir: dir}

	srcName := "report_123.pdf"
	require.NoError(t, os.WriteFile(dir+"/"+srcName, []byte("data"), 0644))

	names, copied, err := tm.copyAttachmentsShadow([]string{srcName})
	require.NoError(t, err)
	require.Len(t, names, 1)
	require.NotEqual(t, srcName, names[0])
	require.FileExists(t, copied[0])

	// Deleting the source file must not affect the shadow copy.
	require.NoError(t, os.Remove(dir+"/"+srcName))
	require.FileExists(t, copied[0])

	_, _, err = tm.copyAttachmentsShadow([]string{"nope.pdf"})
	require.Error(t, err)
}

func TestFindingAt(t *testing.T) {
	raw, err := json.Marshal(resultEvent("http://a", "fp", "CVE-A", "CVE-B"))
	require.NoError(t, err)

	tgt, cve, err := findingAt(raw, 1)
	require.NoError(t, err)
	require.Equal(t, "http://a", tgt)
	require.Equal(t, "CVE-B", cve)

	_, _, err = findingAt(raw, 5)
	require.Error(t, err)
}

func newDerivedReverify(t *testing.T, tm *TaskManager, id, parent string) {
	t.Helper()
	s := &database.Session{
		ID: id, Username: "alice", TaskType: agent.TaskTypeAIInfraScan,
		Status: TaskStatusDoing, RescanKind: "reverify", ParentSessionID: parent,
		Params: []byte(`{"reverify_source":"` + parent + `","reverify_target":"http://t","reverify_cve":"CVE-1","reverify_used_ai":false}`),
	}
	require.NoError(t, tm.taskStore.CreateSession(s))
}

func TestMaybeFinishReverifyWritesResult(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()

	src := &database.Session{ID: "src1", Username: "alice", TaskType: agent.TaskTypeAIInfraScan, Content: "x", Status: TaskStatusDone, RescanKind: "normal"}
	require.NoError(t, tm.taskStore.CreateSession(src))

	newDerivedReverify(t, tm, "der1", "src1")
	tm.maybeFinishReverify("der1", "resultUpdate", resultEvent("http://t", "nginx/1.0", "CVE-1"))
	msg, err := tm.taskStore.GetLatestSessionEventByType("src1", "reverifyResult")
	require.NoError(t, err)
	var ev ReverifyResultEvent
	require.NoError(t, json.Unmarshal(msg.EventData, &ev))
	require.Equal(t, "reproduced", ev.Result.State)
	require.True(t, ev.Result.Reproduced)

	// The derived task is cleaned up after writing the conclusion.
	_, err = tm.taskStore.GetSession("der1")
	require.Error(t, err)

	newDerivedReverify(t, tm, "der2", "src1")
	tm.maybeFinishReverify("der2", "error", nil)
	msg, err = tm.taskStore.GetLatestSessionEventByType("src1", "reverifyResult")
	require.NoError(t, err)
	require.NoError(t, json.Unmarshal(msg.EventData, &ev))
	require.Equal(t, "error", ev.Result.State)
}

func TestNormalTaskCannotForgeReverify(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()

	src := &database.Session{ID: "src1", Username: "alice", Status: TaskStatusDone, RescanKind: "normal"}
	require.NoError(t, tm.taskStore.CreateSession(src))

	// A normal task whose (client-controlled) params claim to be a re-verify must
	// not write into src1 nor delete itself.
	normal := &database.Session{
		ID: "n1", Username: "alice", Status: TaskStatusDoing, RescanKind: "normal",
		Params: []byte(`{"reverify_source":"src1","reverify_target":"http://t","reverify_cve":"CVE-1"}`),
	}
	require.NoError(t, tm.taskStore.CreateSession(normal))

	tm.maybeFinishReverify("n1", "resultUpdate", resultEvent("http://t", "nginx/1.0", "CVE-1"))

	_, err := tm.taskStore.GetLatestSessionEventByType("src1", "reverifyResult")
	require.Error(t, err) // nothing written to the (forged) source
	if _, err := tm.taskStore.GetSession("n1"); err != nil {
		t.Fatalf("normal task must not be deleted: %v", err)
	}
}

func TestRescanTaskValidation(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()

	_, err := tm.RescanTask("nope", "alice", "t", nil, "")
	require.Error(t, err)

	src := &database.Session{ID: "s1", Username: "alice", TaskType: agent.TaskTypeAIInfraScan, Content: "x", Status: TaskStatusDone, RescanKind: "normal"}
	require.NoError(t, tm.taskStore.CreateSession(src))

	_, err = tm.RescanTask("s1", "bob", "t", nil, "")
	require.Error(t, err) // not owner

	require.NoError(t, tm.taskStore.UpdateSessionStatus("s1", TaskStatusDoing))
	_, err = tm.RescanTask("s1", "alice", "t", nil, "")
	require.Error(t, err) // still running
}

func TestReverifyFindingValidation(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()

	src := &database.Session{ID: "s1", Username: "alice", TaskType: agent.TaskTypeAIInfraScan, Content: "x", Status: TaskStatusDone, RescanKind: "normal"}
	require.NoError(t, tm.taskStore.CreateSession(src))

	_, err := tm.ReverifyFinding("s1", "bob", "t", 0, "")
	require.Error(t, err) // not owner

	_, err = tm.ReverifyFinding("s1", "alice", "t", 0, "")
	require.Error(t, err) // no result stored yet

	require.NoError(t, tm.taskStore.StoreEvent("m1", "s1", "resultUpdate", resultEvent("http://t", "fp", "CVE-1"), 1))
	_, err = tm.ReverifyFinding("s1", "alice", "t", 5, "")
	require.Error(t, err) // index out of range

	src2 := &database.Session{ID: "s2", Username: "alice", TaskType: agent.TaskTypeMcpScan, Status: TaskStatusDone, RescanKind: "normal"}
	require.NoError(t, tm.taskStore.CreateSession(src2))
	_, err = tm.ReverifyFinding("s2", "alice", "t", 0, "")
	require.Error(t, err) // not an Infra task
}
