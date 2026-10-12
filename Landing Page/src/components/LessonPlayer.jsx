import { CheckIcon } from './Icons.jsx';
import { VideoPlayer } from './VideoPlayer.jsx';

// Área principal de una clase: video, título, info y "completada".
export function LessonPlayer({ lesson, moduleTitle, completed, onPlay, onProgress, onEnded, onComplete }) {
  return (
    <article className="clase-main">
      {/* key: al cambiar de clase el reproductor arranca de cero */}
      <VideoPlayer key={lesson.id} video={lesson.video} title={lesson.title} onPlay={onPlay} onProgress={onProgress} onEnded={onEnded} />
      <div className="clase-cabecera">
        <div className="clase-textos">
          <p className="clase-rotulo">
            Clase {String(lesson.order).padStart(2, '0')}
            {moduleTitle ? ` · ${moduleTitle}` : ''}
            {lesson.duration ? ` · ${lesson.duration}` : ''}
          </p>
          <h1 className="display clase-h1">{lesson.title}</h1>
        </div>
        <button type="button" className={completed ? 'btn-completar hecha' : 'btn-completar'} onClick={onComplete} disabled={completed}>
          <span className="btn-completar-check"><CheckIcon size={11} /></span>
          {completed ? 'Completada' : 'Marcar como completada'}
        </button>
      </div>
      <p className="clase-desc">{lesson.description}</p>
    </article>
  );
}
