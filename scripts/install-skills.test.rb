#!/usr/bin/env ruby
# frozen_string_literal: true

require "fileutils"
require "minitest/autorun"
require "open3"
require "tmpdir"

class InstallSkillsTest < Minitest::Test
  def test_force_skips_target_that_is_source
    Dir.mktmpdir do |dir|
      FileUtils.mkdir_p(File.join(dir, "scripts"))
      FileUtils.mkdir_p(File.join(dir, "skills", "sample"))
      FileUtils.cp(File.join(__dir__, "install-skills"), File.join(dir, "scripts", "install-skills"))
      File.write(File.join(dir, "skills", "sample", "SKILL.md"), "---\nname: sample\ndescription: sample\n---\n")

      stdout, stderr, status = Open3.capture3(
        RbConfig.ruby,
        File.join(dir, "scripts", "install-skills"),
        "--target",
        File.join(dir, "skills"),
        "--force",
        "sample"
      )

      assert status.success?, stderr
      assert_includes stderr, "target is source, skipping"
      assert_empty stdout
      assert_path_exists File.join(dir, "skills", "sample", "SKILL.md")
    end
  end

  def test_force_copy_replaces_existing_symlink
    Dir.mktmpdir do |dir|
      FileUtils.mkdir_p(File.join(dir, "repo", "scripts"))
      FileUtils.mkdir_p(File.join(dir, "repo", "skills", "sample"))
      FileUtils.mkdir_p(File.join(dir, "target"))
      FileUtils.cp(File.join(__dir__, "install-skills"), File.join(dir, "repo", "scripts", "install-skills"))
      File.write(File.join(dir, "repo", "skills", "sample", "SKILL.md"), "---\nname: sample\ndescription: sample\n---\n")
      FileUtils.ln_s(File.join(dir, "repo", "skills", "sample"), File.join(dir, "target", "sample"))

      stdout, stderr, status = Open3.capture3(
        RbConfig.ruby,
        File.join(dir, "repo", "scripts", "install-skills"),
        "--target",
        File.join(dir, "target"),
        "--force",
        "--mode",
        "copy",
        "sample"
      )

      assert status.success?, stderr
      assert_includes stdout, "copy sample"
      refute File.symlink?(File.join(dir, "target", "sample"))
      assert_path_exists File.join(dir, "target", "sample", "SKILL.md")
      assert_path_exists File.join(dir, "repo", "skills", "sample", "SKILL.md")
    end
  end
end
