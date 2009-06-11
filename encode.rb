#!/usr/bin/ruby
#
# Copyright 2009 Javeed Shaikh <syscrash2k@gmail.com>
# Copyright 2009 Brenden Matthews <brenden@rty.ca>
#
# Distributed under the terms of the GNU General Public License v3
#

require 'fileutils'

THUMBWIDTH = 120
THUMBHEIGHT = 90

# how much faster the input video should be played when generating the preview
INPUT_SPEED_FACTOR = 6

# how much of the input video we want to sample
MIN_PREVIEW_DURATION = 10 # seconds
MAX_PREVIEW_DURATION = 20 # seconds
IDEAL_DURATION_FACTOR = 0.05 # 5%

# the framerate of the preview; increasing this will make the preview smoother
PREVIEW_FPS = 4

AUDIO_QUALITY = 5
VIDEO_QUALITY = 9
VIDEO_DEFAULT_BITRATE = 1500 # the bitrate is the same as the input typically, but in case we can't determine it, we use this
TMP_PATH = '/tmp'

def video_info(filename)
	f = IO.popen("mplayer -ao null -vo null -msglevel identify=6 -endpos 0 '#{filename}'", "r")
	info = {}
	f.each do |line|
		if line =~ /^ID_(.+)=(.+)/
			info[$1] = $2
		elsif line =~ /^\[mkv\] Track ID (\d+): subtitles \(S_TEXT\/ASS\)/
			info['ASS'] = $1
		end
	end
	if info['VIDEO_BITRATE'].to_i < 1
		# if bitrate reported by mplayer was 0 or something else <1, try using ffmpeg instead
		f = IO.popen("ffmpeg -i '#{filename}' 2>&1", "r")
		f.each do |line|
			if line =~ /.*Duration:.*bitrate: \d+ kb\/s/
				info['VIDEO_BITRATE'] = line.match(/.*Duration:.*bitrate: (\d+) kb\/s/)[1].to_i
			end
		end
	else
		info['VIDEO_BITRATE'] = info['VIDEO_BITRATE'].to_i / 1024
	end
	# pro method of determining whether this is a valid video
	info['FILENAME'] == filename ? info : nil
end

# returns an array [width, height]
def image_size(filename)
	f = IO.popen("file '#{filename}.gif'")
	info = f.readlines[0]
	f.close

	stuff = info.split
	width = stuff[-3].to_i
	height = stuff[-1].to_i

	return [width, height]
end

def generate_preview(input, input_fps, endpos, output, output_still, width)
	# mplayer is not very happy with spaces in the output file name, p awesome
	# this also uses ffmpegthumbnailer as a fallback in case the video is too short for mplayer to catch it (reach out a little bit more to catch it)
	peeview = 'peeview'
	match = input.match(/[A-Za-z0-9]+-/)
	if match
		peeview = match[0].to_s + 'peeview'
	end
	system('mplayer', '-speed', '100', '-vf', 'scale', '-zoom', '-fps', input_fps.to_s, '-xy', THUMBWIDTH.to_s, '-benchmark', '-ao', 'null', '-endpos', endpos.to_s, '-vo', "gif89a:fps=#{PREVIEW_FPS}:output=\"#{TMP_PATH}/#{peeview}.gif\"", input) or return false
	system('mogrify', '-layers', 'optimize', "#{TMP_PATH}/#{peeview}.gif") or (system('ffmpegthumbnailer', '-s', THUMBWIDTH.to_s, '-i', input, '-o', "#{TMP_PATH}/#{peeview}.gif") and system('mogrify', '-layers', 'optimize', "#{TMP_PATH}/#{peeview}.gif")) or return false
	# system('convert', '-coalesce', '-flatten', "#{TMP_PATH}/#{peeview}.gif", "#{TMP_PATH}/#{peeview}-still.gif") or return false
	system('ffmpegthumbnailer', '-s', width.to_s, '-f', '-i', input, '-o', "#{TMP_PATH}/#{peeview}-still.gif") or return false
	system('mogrify', "#{TMP_PATH}/#{peeview}-still.gif") or return false
	FileUtils::mv("#{TMP_PATH}/#{peeview}.gif", output)
	FileUtils::mv("#{TMP_PATH}/#{peeview}-still.gif", output_still)
end

if ARGV.empty?
	$stderr.puts "usage: #{$0} input-video-file <tmp path>"
	exit 1
end

input = ARGV[0]
if ARGV[1]
	TMP_PATH = ARGV[1]
end

output = "#{input}.ogg"
thumbnail = "#{input}.gif"
thumbnail_still = "#{input}-still.gif"

(info = video_info(input)) or exit 1
#require 'pp'; pp info


cleanup = Array.new()

if info.has_key? 'ASS'
	subtitled_yuv = File.join(TMP_PATH, 'subtitled.yuv')
	subtitled_avi = File.join(TMP_PATH, 'subtitled.avi')
	subtitled_mkv = File.join(TMP_PATH, 'subtitled.mkv')
	cleanup << subtitled_yuv
	cleanup << subtitled_avi
	cleanup << subtitled_mkv
	# burn those subtitles in
	system('mplayer', '-speed', '100', '-ass', '-ao', 'null', '-vo', "yuv4mpeg:file=#{subtitled_yuv}", input) or exit 1
	# lossless codec for intermediate stuff, pretty advanced
	system('mencoder', subtitled_yuv, '-ovc', 'lavc', '-lavcopts', 'vcodec=ffv1', '-o', subtitled_avi) or exit 1
	system('mkvmerge', '-o', subtitled_mkv, '-D', input, subtitled_avi) or exit 1

	# work with the haxed mkv from now on
	input = subtitled_mkv
end

input_bitrate = info['VIDEO_BITRATE'].to_i # maintain the bitrate so the file size is <= the input
if input_bitrate < 1
	# uhm, weird case
	input_bitrate = VIDEO_DEFAULT_BITRATE
end
# don't re-encode if you don't have to
if (info['DEMUXER'] != 'ogg') or (info['VIDEO_FORMAT'] != 'theo') or (info['AUDIO_FORMAT'] != 'vrbs')
	system('ffmpeg2theora', '--audioquality', AUDIO_QUALITY.to_s, '--videoquality', VIDEO_QUALITY.to_s, '--optimize', '--videobitrate', input_bitrate.to_s, '-o', output, input) # or exit 1 ignored
else
	FileUtils::cp(input, output)
end

input_fps = info['VIDEO_FPS'].to_i * INPUT_SPEED_FACTOR
endpos = info['LENGTH'].to_i * IDEAL_DURATION_FACTOR
# sometimes mplayer can't determine the input length, in which case we'll take 30 seconds
if endpos < MIN_PREVIEW_DURATION
	endpos = MIN_PREVIEW_DURATION
elsif endpos > MAX_PREVIEW_DURATION
	endpos = MAX_PREVIEW_DURATION
end
endpos = endpos * INPUT_SPEED_FACTOR
generate_preview(input, input_fps.to_i, endpos.to_i, thumbnail, thumbnail_still, THUMBWIDTH) or exit 1

# does this thing fit in the thumbnail box?
width, height = image_size thumbnail
if height > THUMBHEIGHT
	# it doesn't! fit to height instead
	generate_preview(input, thumbnail, thumbnail_still, THUMBHEIGHT * width / height) or exit 1
end


cleanup.each do |file|
	File.unlink(file)
end
