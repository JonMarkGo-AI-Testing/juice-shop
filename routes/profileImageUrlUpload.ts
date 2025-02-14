/*
 * Copyright (c) 2014-2024 Bjoern Kimminich & the OWASP Juice Shop contributors.
 * SPDX-License-Identifier: MIT
 */

import { createWriteStream } from 'fs'
import { type Request, type Response, type NextFunction } from 'express'
import logger from '../lib/logger'
import { UserModel } from '../models/user'
import * as utils from '../lib/utils'
import { authenticatedUsers } from '../lib/insecurity'
import request from 'request'

module.exports = function profileImageUrlUpload () {
  return (req: Request, res: Response, next: NextFunction) => {
    if (req.body.imageUrl !== undefined) {
      const url = req.body.imageUrl
      
      // Validate URL format and protocol
      if (!url || typeof url !== 'string' || !url.match(/^https?:\/\/.+/i)) {
        return next(new Error('Invalid image URL format'))
      }

      // Whitelist allowed domains and protocols
      try {
        const parsedUrl = new URL(url)
        const allowedDomains = ['imgur.com', 'githubusercontent.com', 'googleusercontent.com'] // Add more trusted domains as needed
        if (!allowedDomains.some(domain => parsedUrl.hostname.endsWith(domain))) {
          return next(new Error('Domain not allowed for security reasons'))
        }
        if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
          return next(new Error('Only HTTP(S) protocols are allowed'))
        }
      } catch (e) {
        return next(new Error('Invalid URL'))
      }

      if (url.match(/(.)*solve\/challenges\/server-side(.)*/) !== null) req.app.locals.abused_ssrf_bug = true
      const loggedInUser = authenticatedUsers.get(req.cookies.token)
      if (loggedInUser) {
        const imageRequest = request
          .get(url, {
            timeout: 5000,
            followRedirect: true,
            maxRedirects: 2
          })
          .on('error', function (err: unknown) {
            UserModel.findByPk(loggedInUser.data.id).then(async (user) => { 
              if (user) await user.update({ profileImage: url })
            }).catch((error: Error) => { next(error) })
            logger.warn(`Error retrieving user profile image: ${utils.getErrorMessage(err)}; using image link directly`)
          })
          .on('response', function (res: Response) {
            if (res.statusCode === 200) {
              const allowedExtensions = ['jpg', 'jpeg', 'png', 'svg', 'gif']
              const ext = allowedExtensions.includes(url.split('.').slice(-1)[0].toLowerCase()) ? url.split('.').slice(-1)[0].toLowerCase() : 'jpg'
              const safeFilename = `${loggedInUser.data.id}.${ext}`.replace(/[^a-zA-Z0-9._-]/g, '')
              const uploadPath = `frontend/dist/frontend/assets/public/images/uploads/${safeFilename}`
              imageRequest.pipe(createWriteStream(uploadPath))
              UserModel.findByPk(loggedInUser.data.id).then(async (user) => {
                if (user) await user.update({ profileImage: `/assets/public/images/uploads/${safeFilename}` })
              }).catch((error: Error) => { next(error) })
            } else {
              UserModel.findByPk(loggedInUser.data.id).then(async (user) => {
                if (user) await user.update({ profileImage: url })
              }).catch((error: Error) => { next(error) })
            }
          })
      } else {
        next(new Error('Blocked illegal activity by ' + req.socket.remoteAddress))
      }
    }
    res.location(process.env.BASE_PATH + '/profile')
    res.redirect(process.env.BASE_PATH + '/profile')
  }
}
